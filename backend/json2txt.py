import json
import os

# 假设 DeepSeek Python SDK 可用
try:
    from deepseek import DeepSeekLLM
    LLM_AVAILABLE = True
except ImportError:
    print("[WARN] DeepSeek LLM SDK 未安装，LLM 功能将被禁用")
    LLM_AVAILABLE = False


def json_to_txt_values_only(json_path, txt_path, flatten=True, use_llm=False, llm_api_key=None):
    """
    将 JSON 文件转换为 TXT 文件，只保留值，每个值分行，并可调用 DeepSeek LLM 做总结。
    
    参数:
    - json_path: str, JSON 文件路径
    - txt_path: str, 输出 TXT 文件路径
    - flatten: bool, 是否将嵌套 JSON 展平成文本
    - use_llm: bool, 是否调用 LLM 做总结
    - llm_api_key: str, LLM API key
    """
    
    def flatten_json_values(y):
        """
        将 JSON 展平成只有 value 的列表
        """
        values = []
        if isinstance(y, dict):
            for v in y.values():
                values.extend(flatten_json_values(v))
        elif isinstance(y, list):
            for item in y:
                values.extend(flatten_json_values(item))
        else:
            values.append(str(y))
        return values

    # 读取 JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 初始化 LLM
    llm = DeepSeekLLM(api_key=llm_api_key) if use_llm and LLM_AVAILABLE else None

    # 打开 TXT 文件
    with open(txt_path, 'w', encoding='utf-8') as f:
        entries = data if isinstance(data, list) else [data]
        for i, item in enumerate(entries):
            f.write(f"### Entry {i+1} ###\n")
            values = flatten_json_values(item) if flatten else [str(item)]
            for val in values:
                f.write(val + "\n")
            
            # 调用 LLM 做总结
            if llm:
                text_for_llm = "\n".join(values)
                summary = llm.summarize(text_for_llm)
                f.write("\n### LLM Summary ###\n")
                f.write(summary + "\n")
            
            f.write("\n\n")
    
    print(f"[INFO] JSON 已转换为 TXT（仅保留值）: {txt_path}")
    if llm:
        print("[INFO] 已使用 DeepSeek LLM 生成总结。")


# if __name__ == "__main__":
#     json_file = "/content/summary_report_20260312_170235.json"
#     txt_file = "output_values_only.txt"
#     json_to_txt_values_only(json_file, txt_file, use_llm=True, llm_api_key="sk-6f46b3f825c345b3a95fd87813543324")