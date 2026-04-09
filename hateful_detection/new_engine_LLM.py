import copy
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
import pytorch_lightning as pl
import torchmetrics
from transformers import CLIPModel, AutoModelForCausalLM, AutoTokenizer
import os
import json
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: openai package not installed. Install with: pip install openai")


class SimpleGNNLayer(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.lin = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(0.1)
        self.norm = nn.LayerNorm(dim)

    def forward(self, x, edge_index):
        # x: [N, D], edge_index: [2, E]
        src, dst = edge_index
        agg = torch.zeros_like(x)
        agg.index_add_(0, dst, x[src])
        out = self.lin(self.norm(x + agg))
        out = F.relu(out)
        out = self.dropout(out)
        return x + out  # residual


class PCMModule(nn.Module):
    """Presupposed Context Module: h_PC = (W1 h_v + b1) ⊙ (W2 h_t + b2)."""
    def __init__(self, dim):
        super().__init__()
        self.lin_v = nn.Sequential(
            nn.Linear(dim, dim), nn.ReLU(), nn.Dropout(0.1), nn.LayerNorm(dim)
        )
        self.lin_t = nn.Sequential(
            nn.Linear(dim, dim), nn.ReLU(), nn.Dropout(0.1), nn.LayerNorm(dim)
        )

    def forward(self, h_v, h_t):
        # h_v: [B, D], h_t: [B, D]
        v_ctx = self.lin_v(h_v)
        t_ctx = self.lin_t(h_t)
        return v_ctx * t_ctx  # Hadamard product -> [B, D]


class FACTModule(nn.Module):
    """False Claims Module = SPM (LLM prompt projection) + CRM (graph + GNN)."""
    def __init__(self, dim, llm_dim=None, top_k=8, llm_name: str = 'gpt-5', 
                 use_api: bool = True, api_key: str = None, api_base: str = None):
        super().__init__()
        self.top_k = top_k
        self.llm_dim = llm_dim or dim
        self.llm_name = llm_name
        
        # 硬编码 API 配置
        self.api_key = "sk-zk21884c49fc398427914f99fc30171ecb068f998dc6f05b"
        self.api_base = "https://api.zhizengzeng.com/v1"
        self.use_api = True
        
        # 初始化 API 客户端
        if HAS_OPENAI:
            try:
                self.api_client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)
                print(f"✓ Using GPT-5 API mode")
                print(f"  API Base: {self.api_base}")
                # API 模式下不需要本地模型
                self.llm = None
                self.llm_tokenizer = None
                # API 返回的 embedding 投影层
                self.llm_in_proj = nn.Sequential(
                    nn.Linear(self.llm_dim, self.llm_dim),
                    nn.GELU(),
                    nn.Dropout(0.1),
                    nn.Linear(self.llm_dim, self.llm_dim),
                    nn.LayerNorm(self.llm_dim)
                )
            except Exception as e:
                print(f"ERROR: Failed to initialize GPT-5 API client: {e}")
                raise RuntimeError(f"Cannot proceed without API access: {e}")
        else:
            raise ImportError("openai package is required. Install with: pip install openai")
        # MLP to map encodings into LLM space for prompt tokens
        self.to_llm = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(dim * 2, self.llm_dim),
            nn.LayerNorm(self.llm_dim)
        )

        # simple GNN for CRM
        self.gnn = SimpleGNNLayer(dim)
        self.gnn2 = SimpleGNNLayer(dim)
        # MLP for social perception vector pooling
        self.sp_pool = nn.Sequential(
            nn.Linear(self.llm_dim, self.llm_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(self.llm_dim, dim),
            nn.LayerNorm(dim)
        )

    def build_spm(self, Hv, Ht, texts):
        # project to llm space and concatenate: [B, P+T, d_llm]
        Hv_llm = self.to_llm(Hv)
        Ht_llm = self.to_llm(Ht)
        prompt = torch.cat([Hv_llm, Ht_llm], dim=1)
        
        # 使用 GPT-5 API 获取 embeddings（批量调用优化）
        try:
            B = len(texts)
            # 批量调用 embedding API（一次性处理整个 batch）
            embed_response = self.api_client.embeddings.create(
                input=texts,  # 直接传入整个列表，API 会批量处理
                model="text-embedding-ada-002"
            )
            embeddings_list = [item.embedding for item in embed_response.data]
            
            # 转换为 tensor
            api_embeddings = torch.tensor(embeddings_list, device=prompt.device, dtype=prompt.dtype)
            
            # 调整维度到 llm_dim
            if api_embeddings.size(-1) != self.llm_dim:
                if not hasattr(self, 'embed_resize'):
                    self.embed_resize = nn.Linear(api_embeddings.size(-1), self.llm_dim).to(prompt.device)
                api_embeddings = self.embed_resize(api_embeddings)
            
            last_hidden = api_embeddings.unsqueeze(1)  # [B, 1, D]
            last_hidden = self.llm_in_proj(last_hidden)
            h_sp = self.sp_pool(last_hidden.mean(dim=1))
            
            # 使用投影 tokens 近似注意力矩阵
            A_text = torch.einsum('bid,bjd->bij', last_hidden, last_hidden) / math.sqrt(last_hidden.size(-1))
            proj_tokens = prompt.mean(dim=1, keepdim=True)
            A_vis = torch.einsum('bnd,bmd->bnm', proj_tokens, proj_tokens)
            N = prompt.size(1)
            L = A_text.size(-1)
            if L != N:
                A_text = F.interpolate(A_text.unsqueeze(1), size=(N, N), mode='bilinear', align_corners=False).squeeze(1)
            A = (A_text + A_vis) / 2.0
            return h_sp, A
            
        except Exception as e:
            print(f"GPT-5 API call failed: {e}. Using fallback attention.")
            # Fallback: 使用简单的点积注意力
            scale = math.sqrt(self.llm_dim)
            A = torch.einsum('bnd,bmd->bnm', prompt, prompt) / scale
            h_sp = self.sp_pool(prompt.mean(dim=1))
            return h_sp, A

    def build_crm_edges(self, A, text_len, patch_len):
        # Build E_tt (chain), E_pp (grid), E_tp (Top-K from text to patches)
        B, N, _ = A.shape
        edges_all = []
        offset = 0
        for b in range(B):
            # token offsets within batch
            # E_tt: 0..(text_len-1)
            e = []
            for i in range(text_len - 1):
                e.append((offset + i, offset + i + 1))
                e.append((offset + i + 1, offset + i))
            # E_pp: grid adjacency for patches following text tokens
            grid_side = int(math.sqrt(patch_len))
            base = offset + text_len
            for r in range(grid_side):
                for c in range(grid_side):
                    idx = base + r * grid_side + c
                    if r + 1 < grid_side:
                        e.append((idx, idx + grid_side))
                        e.append((idx + grid_side, idx))
                    if c + 1 < grid_side:
                        e.append((idx, idx + 1))
                        e.append((idx + 1, idx))
            # E_tp: Top-K attention from each text token to patches
            # A segment: text-to-patch block → rows 0..text_len-1, cols text_len..text_len+patch_len-1
            A_tp = A[b, :text_len, text_len:text_len+patch_len]
            K = min(self.top_k, patch_len)
            topk_idx = torch.topk(A_tp, k=K, dim=-1).indices  # [text_len, K]
            for t in range(text_len):
                for k in range(K):
                    p = topk_idx[t, k].item()
                    e.append((offset + t, base + p))
                    e.append((base + p, offset + t))
            edges = torch.tensor(e, dtype=torch.long)
            edges_all.append(edges)
            offset += N
        edges_all = torch.cat(edges_all, dim=0)  # [E, 2]
        return edges_all.t().contiguous()  # [2, E]

    def forward(self, Hv, Ht, texts):
        # Hv: [B,P,D], Ht: [B,T,D], texts: list[str] length B
        B, P, D = Hv.shape
        T = Ht.shape[1]
        if texts is None:
            texts = ["Are there false claims?" for _ in range(B)]
        h_sp, A = self.build_spm(Hv, Ht, texts)
        # build CRM graph and run GNN over encs (concatenate encs)
        encs = torch.cat([Ht, Hv], dim=1)  # [B, T+P, D]
        edge_index = self.build_crm_edges(A, text_len=T, patch_len=P)
        edge_index = edge_index.to(encs.device)
        x = encs.reshape(B * (T + P), D)
        x = self.gnn(x, edge_index)
        x = self.gnn2(x, edge_index)
        x = x.reshape(B, T + P, D)
        h_cr = x.mean(dim=1)  # mean pooling
        return h_sp, h_cr



class NewClassifier(pl.LightningModule):
    def __init__(self, args):
        super().__init__()
        self.save_hyperparameters(vars(args))
        self.lr = args.lr
        self.weight_decay = args.weight_decay
        # Load CLIP and optionally freeze encoders
        self.clip = CLIPModel.from_pretrained(args.clip_pretrained_model)
        self.image_encoder = copy.deepcopy(self.clip.vision_model)
        self.text_encoder = copy.deepcopy(self.clip.text_model)
        if args.freeze_image_encoder:
            for p in self.image_encoder.parameters():
                p.requires_grad = False
        if args.freeze_text_encoder:
            for p in self.text_encoder.parameters():
                p.requires_grad = False
        # Projection to common dim with MLP instead of simple linear
        self.proj_dim = self.clip.projection_dim
        # infer hidden sizes
        d_img = getattr(self.image_encoder.config, 'hidden_size', self.clip.config.vision_config.hidden_size)
        d_txt = getattr(self.text_encoder.config, 'hidden_size', self.clip.config.text_config.hidden_size)
        # MLP projection for image features
        self.img_proj = nn.Sequential(
            nn.Linear(d_img, d_img),
            nn.GELU(),
            nn.Dropout(0.15),
            nn.Linear(d_img, self.proj_dim),
            nn.LayerNorm(self.proj_dim)
        )
        # MLP projection for text features
        self.txt_proj = nn.Sequential(
            nn.Linear(d_txt, d_txt),
            nn.GELU(),
            nn.Dropout(0.15),
            nn.Linear(d_txt, self.proj_dim),
            nn.LayerNorm(self.proj_dim)
        )
        # PCM and FACT (使用硬编码的 GPT-5 API)
        self.pcm = PCMModule(self.proj_dim)
        self.fact = FACTModule(self.proj_dim, llm_dim=self.proj_dim, llm_name='gpt-5')
        # Classifier
        self.classifier = nn.Sequential(
            nn.Linear(self.proj_dim * 3, self.proj_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(self.proj_dim, 1)
        )
        # Auxiliary heads for per-modality losses to mimic main.py logging style
        self.img_head = nn.Linear(self.proj_dim, 1)
        self.txt_head = nn.Linear(self.proj_dim, 1)
        # Metrics
        self.auroc = torchmetrics.AUROC(task='binary')
        self.f1 = torchmetrics.F1Score(task='binary')
        self.acc = torchmetrics.Accuracy(task='binary')


    def encode_image(self, pixel_values):
        # pixel_values: [B, 3, H, W]
        out = self.image_encoder(pixel_values, output_hidden_states=True)
        # pooled embedding
        h_v_img = out.pooler_output  # [B, d_img]
        h_v = self.img_proj(h_v_img)  # [B, D]
        # patch-level embeddings from last hidden
        Hv_img = out.hidden_states[-1]  # [B, 1+P, d_img] (includes CLS)
        Hv_img = Hv_img[:, 1:, :]  # drop CLS
        Hv = self.img_proj(Hv_img)  # [B, P, D]
        return Hv, h_v

    def encode_text(self, input_ids, attention_mask):
        out = self.text_encoder(input_ids=input_ids, attention_mask=attention_mask, output_hidden_states=True)
        h_t_txt = out.pooler_output  # [B, d_txt]
        h_t = self.txt_proj(h_t_txt)  # [B, D]
        Ht_txt = out.hidden_states[-1]  # [B, T, d_txt]
        Ht = self.txt_proj(Ht_txt)  # [B, T, D]
        return Ht, h_t

    def build_prompt(self, Hv, Ht):
        # Placeholder: use mean of Hv/Ht as prompt tokens
        return torch.cat([Hv.mean(dim=1, keepdim=True), Ht.mean(dim=1, keepdim=True)], dim=1)  # [B, 2, D]

    def forward(self, batch):
        pixel_values = batch['pixel_values'].squeeze(0)
        Hv, h_v = self.encode_image(pixel_values)       # [B,P,D], [B,D]
        Ht, h_t = self.encode_text(batch['input_ids'], batch['attention_mask'])  # [B,T,D], [B,D]
        # PCM
        h_pc = self.pcm(h_v, h_t)  # [B, D]
        # FACT (SPM + CRM)
        texts_for_llm = ["Are there false claims? " for _ in range(Hv.size(0))]
        h_sp, h_cr = self.fact(Hv, Ht, texts_for_llm)  # [B, D], [B, D]
        # Classifier: concat h_PC, h_SP, h_CR
        logits = self.classifier(torch.cat([h_pc, h_sp, h_cr], dim=-1)).squeeze(-1)  # [B]
        return logits



    def training_step(self, batch, batch_idx):
        # Forward for main classifier
        pixel_values = batch['pixel_values'].squeeze(0)
        Hv, h_v = self.encode_image(pixel_values)
        Ht, h_t = self.encode_text(batch['input_ids'], batch['attention_mask'])
        h_pc = self.pcm(h_v, h_t)
        texts_for_llm = ["Are there false claims? " for _ in range(Hv.size(0))]
        h_sp, h_cr = self.fact(Hv, Ht, texts_for_llm)
        main_logits = self.classifier(torch.cat([h_pc, h_sp, h_cr], dim=-1)).squeeze(-1)

        labels = batch['labels'].float()
        # Auxiliary modality-specific logits
        img_logits = self.img_head(h_v).squeeze(-1)
        txt_logits = self.txt_head(h_t).squeeze(-1)

        image_loss = F.binary_cross_entropy_with_logits(img_logits, labels)
        text_loss = F.binary_cross_entropy_with_logits(txt_logits, labels)
        cls_loss = F.binary_cross_entropy_with_logits(main_logits, labels)
        total_loss = cls_loss + 0.5 * (image_loss + text_loss)

        # Metrics on main logits
        preds = (torch.sigmoid(main_logits) > 0.5).long()
        valid_mask = (labels >= 0) & (labels <= 1)
        if valid_mask.sum() > 0:
            valid_logits = torch.sigmoid(main_logits[valid_mask])
            valid_preds = preds[valid_mask]
            valid_labels = labels[valid_mask].int()
            self.log('train/auroc', self.auroc(valid_logits, valid_labels), prog_bar=True, on_step=True, on_epoch=False)
            self.log('train/accuracy', self.acc(valid_preds, valid_labels), prog_bar=True, on_step=True, on_epoch=False)
            self.log('train/f1', self.f1(valid_preds, valid_labels), prog_bar=False, on_step=True, on_epoch=False)

        # Log losses following original main style
        self.log('train/total_loss', total_loss, prog_bar=True, on_step=True, on_epoch=False)
        self.log('train/image_loss', image_loss, prog_bar=False, on_step=True, on_epoch=False)
        self.log('train/text_loss', text_loss, prog_bar=False, on_step=True, on_epoch=False)
        self.log('train/loss', cls_loss, prog_bar=True, on_step=True, on_epoch=False)
        return total_loss

    def validation_step(self, batch, batch_idx):
        logits = self(batch)
        labels = batch['labels'].float()
        loss = F.binary_cross_entropy_with_logits(logits, labels)
        preds = (torch.sigmoid(logits) > 0.5).long()
        acc = (preds == labels.long()).float().mean()
        self.log('val/loss', loss, prog_bar=True)
        self.log('val/acc', acc, prog_bar=True)
        # Filter out samples with label -1 for metrics (torchmetrics only accepts [0, 1])
        valid_mask = (labels >= 0) & (labels <= 1)
        if valid_mask.sum() > 0:
            valid_logits = torch.sigmoid(logits[valid_mask])
            valid_preds = preds[valid_mask]
            valid_labels = labels[valid_mask].int()
            self.log('val/auroc', self.auroc(valid_logits, valid_labels), prog_bar=True)
            self.log('val/f1', self.f1(valid_preds, valid_labels), prog_bar=True)
        return {'loss': loss, 'acc': acc}


    def test_step(self, batch, batch_idx, dataloader_idx: int = 0):
        logits = self(batch)
        labels = batch['labels'].float()
        loss = F.binary_cross_entropy_with_logits(logits, labels)
        preds = (torch.sigmoid(logits) > 0.5).long()
        acc = (preds == labels.long()).float().mean()
        prefix = f'test{dataloader_idx}'
        self.log(f'{prefix}/loss', loss, prog_bar=True)
        self.log(f'{prefix}/acc', acc, prog_bar=True)
        # Filter out samples with label -1 for metrics (torchmetrics only accepts [0, 1])
        valid_mask = (labels >= 0) & (labels <= 1)
        if valid_mask.sum() > 0:
            valid_logits = torch.sigmoid(logits[valid_mask])
            valid_preds = preds[valid_mask]
            valid_labels = labels[valid_mask].int()
            self.log(f'{prefix}/auroc', self.auroc(valid_logits, valid_labels), prog_bar=True)
            self.log(f'{prefix}/f1', self.f1(valid_preds, valid_labels), prog_bar=True)
        return {'loss': loss, 'acc': acc}

    def configure_optimizers(self):
        return torch.optim.AdamW(
            filter(lambda p: p.requires_grad, self.parameters()),
            lr=self.lr,
            weight_decay=self.weight_decay,
        )
