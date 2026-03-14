/* ============================================================================
   全局变量
   ============================================================================ */

let currentTaskId = null;
let pollInterval = null;

/* ============================================================================
   DOM 元素获取
   ============================================================================ */

function getDOMElements() {
    return {
        // 表单
        form: document.getElementById('searchForm'),
        apiKey1Input: document.getElementById('api_key_1'),
        apiKey2Input: document.getElementById('api_key_2'),
        queryInput: document.getElementById('query'),
        submitBtn: document.getElementById('startBtn'),

        // 分区
        inputSection: document.querySelector('.input-section'),
        progressSection: document.getElementById('progressSection'),
        errorSection: document.getElementById('errorSection'),
        resultSection: document.getElementById('resultSection'),

        // 进度条
        progressBarFill: document.getElementById('progressBar'),
        progressText: document.getElementById('progressPercent'),
        statusMessage: document.getElementById('statusMessage'),
        spinner: document.getElementById('spinner'),

        // 错误
        errorBox: document.getElementById('errorBox'),
        errorTitle: document.getElementById('errorTitle'),
        errorMessage: document.getElementById('errorMessage'),
        retryBtn: document.getElementById('retryBtn'),

        // 结果
        resultSummary: document.getElementById('resultSummary'),
        resultsList: document.getElementById('resultsList'),
        downloadBtn: document.getElementById('downloadBtn'),
        newSearchBtn: document.getElementById('newSearchBtn')
    };
}

/* ============================================================================
   初始化
   ============================================================================ */

document.addEventListener('DOMContentLoaded', function () {
    const elements = getDOMElements();

    console.log('初始化 MARDS Web UI...');
    console.log('DOM 元素：', elements);

    // 直接绑定提交按钮点击事件
    if (elements.submitBtn) {
        console.log('✓ 成功绑定开始搜索按钮');
        elements.submitBtn.addEventListener('click', function (e) {
            e.preventDefault();
            console.log('🔍 开始搜索按钮被点击');
            startSearch();
        });
    } else {
        console.error('✗ 错误：找不到开始搜索按钮（ID: startBtn）');
    }

    // 绑定表单提交
    if (elements.form) {
        elements.form.addEventListener('submit', function (e) {
            e.preventDefault();
            startSearch();
        });
    }

    // 绑定重试按钮
    if (elements.retryBtn) {
        elements.retryBtn.addEventListener('click', function () {
            resetForm();
        });
    }

    // 绑定下载按钮
    if (elements.downloadBtn) {
        elements.downloadBtn.addEventListener('click', function () {
            downloadResults();
        });
    }

    // 绑定新搜索按钮
    if (elements.newSearchBtn) {
        elements.newSearchBtn.addEventListener('click', function () {
            resetForm();
        });
    }
});

/* ============================================================================
   开始搜索
   ============================================================================ */

async function startSearch() {
    const elements = getDOMElements();

    // 验证输入
    if (!validateInputs()) {
        displayError('请填写所有必要字段');
        return;
    }

    // 禁用按钮和输入
    elements.submitBtn.disabled = true;
    elements.apiKey1Input.disabled = true;
    elements.apiKey2Input.disabled = true;
    elements.queryInput.disabled = true;

    // 显示进度区域
    showProgressSection();

    try {
        // 发送任务启动请求
        const response = await fetch('/api/start-task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                api_key_1: elements.apiKey1Input.value.trim(),
                api_key_2: elements.apiKey2Input.value.trim(),
                query: elements.queryInput.value.trim()
            })
        });

        if (!response.ok) {
            throw new Error('启动任务失败：' + response.status);
        }

        const data = await response.json();
        currentTaskId = data.task_id;

        // 开始轮询状态
        startPolling();

    } catch (error) {
        console.error('错误：', error);
        displayError('启动搜索失败：' + error.message);
        resetFormButtons();
    }
}

/* ============================================================================
   验证输入
   ============================================================================ */

function validateInputs() {
    const elements = getDOMElements();

    if (!elements.apiKey1Input.value.trim()) {
        return false;
    }
    if (!elements.apiKey2Input.value.trim()) {
        return false;
    }
    if (!elements.queryInput.value.trim()) {
        return false;
    }

    return true;
}

/* ============================================================================
   轮询状态
   ============================================================================ */

function startPolling() {
    const elements = getDOMElements();

    // 立即轮询一次
    pollTaskStatus();

    // 每 1 秒轮询一次
    pollInterval = setInterval(() => {
        pollTaskStatus();
    }, 1000);
}

async function pollTaskStatus() {
    if (!currentTaskId) return;

    try {
        const response = await fetch(`/api/task-status/${currentTaskId}`);

        if (!response.ok) {
            if (response.status === 404) {
                displayError('任务未找到');
                stopPolling();
                resetFormButtons();
            }
            return;
        }

        const data = await response.json();
        const progress = data.progress || 0;
        const status = data.status || 'running';
        const message = data.message || '处理中...';

        // 更新进度显示
        displayProgress(progress, message);

        // 如果任务完成
        if (status === 'completed') {
            stopPolling();
            fetchTaskResult();
        }
        // 如果任务失败
        else if (status === 'failed') {
            stopPolling();
            const error = data.error || '任务执行失败';
            displayError(error);
            resetFormButtons();
        }

    } catch (error) {
        console.error('轮询错误：', error);
        stopPolling();
        displayError('获取任务状态失败：' + error.message);
        resetFormButtons();
    }
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

/* ============================================================================
   获取任务结果
   ============================================================================ */

async function fetchTaskResult() {
    if (!currentTaskId) return;

    try {
        const response = await fetch(`/api/task-result/${currentTaskId}`);

        if (!response.ok) {
            throw new Error('获取结果失败：' + response.status);
        }

        const data = await response.json();
        displayResult(data.result || {});
        resetFormButtons();

    } catch (error) {
        console.error('获取结果错误：', error);
        displayError('获取结果失败：' + error.message);
        resetFormButtons();
    }
}

/* ============================================================================
   显示进度
   ============================================================================ */

function displayProgress(progress, message) {
    const elements = getDOMElements();

    if (elements.progressBarFill) {
        elements.progressBarFill.style.width = progress + '%';
    }

    if (elements.progressText) {
        elements.progressText.textContent = Math.round(progress) + '%';
    }

    if (elements.statusMessage) {
        elements.statusMessage.textContent = message || '处理中...';
    }
}

/* ============================================================================
   显示结果
   ============================================================================ */

function displayResult(result) {
    const elements = getDOMElements();

    // 隐藏进度区域
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }

    // 隐藏错误区域
    if (elements.errorSection) {
        elements.errorSection.style.display = 'none';
    }

    // 显示结果区域
    if (elements.resultSection) {
        elements.resultSection.style.display = 'block';
    }

    // 显示摘要
    const query = elements.queryInput.value.trim();
    const resultCount = (result.results && Array.isArray(result.results)) ? result.results.length : 0;
    const subQuestions = (result.sub_questions && Array.isArray(result.sub_questions)) ? result.sub_questions.length : 0;
    const globalUncertainty = result.global_uncertainty || 0.0;
    const confidence = ((1 - globalUncertainty) * 100).toFixed(1);

    if (elements.resultSummary) {
        elements.resultSummary.innerHTML = `
            <p><strong>🔍 搜索查询：</strong> ${escapeHtml(query)}</p>
            <p><strong>📊 分析维度：</strong> ${subQuestions} 个子问题</p>
            <p><strong>📚 检索结果：</strong> ${resultCount} 个来源</p>
            <p><strong>🎯 置信度：</strong> ${confidence}% (不确定性: ${(globalUncertainty * 100).toFixed(1)}%)</p>
            <p><strong>🔄 迭代次数：</strong> ${result.loop_count || 0}</p>
            <p><strong>⏰ 完成时间：</strong> ${new Date().toLocaleString('zh-CN')}</p>
        `;
    }

    // 显示结果列表
    if (elements.resultsList) {
        elements.resultsList.innerHTML = '';
        
        // 如果有 synthesis_report，优先显示完整报告
        if (result.synthesis_report) {
            const reportSection = document.createElement('div');
            reportSection.className = 'synthesis-report';
            reportSection.innerHTML = `
                <h3>📝 MARDS 综合分析报告</h3>
                <div class="report-content">
                    <pre style="white-space: pre-wrap; font-family: inherit; background: #f9f9f9; padding: 20px; border-radius: 8px; line-height: 1.6;">${escapeHtml(result.synthesis_report)}</pre>
                </div>
                <hr style="margin: 30px 0;">
            `;
            elements.resultsList.appendChild(reportSection);
        }
        
        // 显示子问题（如果有）
        if (result.sub_questions && result.sub_questions.length > 0) {
            const subQuestionsSection = document.createElement('div');
            subQuestionsSection.className = 'sub-questions-section';
            subQuestionsSection.innerHTML = `
                <h3>🔎 问题分解</h3>
                <ul style="list-style: none; padding: 0;">
                    ${result.sub_questions.map((q, i) => `
                        <li style="margin: 10px 0; padding: 10px; background: #f0f7ff; border-left: 4px solid #4f46e5; border-radius: 4px;">
                            <strong>${i + 1}.</strong> ${escapeHtml(q)}
                        </li>
                    `).join('')}
                </ul>
                <hr style="margin: 30px 0;">
            `;
            elements.resultsList.appendChild(subQuestionsSection);
        }

        // 显示搜索结果
        if (result.results && Array.isArray(result.results) && result.results.length > 0) {
            const resultsHeader = document.createElement('h3');
            resultsHeader.textContent = '📚 检索来源';
            resultsHeader.style.marginBottom = '20px';
            elements.resultsList.appendChild(resultsHeader);
            
            result.results.forEach((item, index) => {
                const resultItem = createResultItem(item, index);
                elements.resultsList.appendChild(resultItem);
            });
        } else if (!result.synthesis_report) {
            elements.resultsList.innerHTML = '<p style="text-align: center; color: #999;">没有找到结果</p>';
        }
    }
}

function createResultItem(item, index) {
    const div = document.createElement('div');
    div.className = 'result-item';

    const title = item.title || `结果 ${index + 1}`;
    const url = item.url || '';
    const snippet = item.snippet || item.content || '';

    div.innerHTML = `
        <h4>${escapeHtml(title)}</h4>
        ${url ? `<a href="${escapeHtml(url)}" class="url" target="_blank">${escapeHtml(url)}</a>` : ''}
        <p class="snippet">${escapeHtml(snippet)}</p>
    `;

    return div;
}

/* ============================================================================
   显示错误
   ============================================================================ */

function displayError(message) {
    const elements = getDOMElements();

    // 隐藏进度区域
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }

    // 隐藏结果区域
    if (elements.resultSection) {
        elements.resultSection.style.display = 'none';
    }

    // 显示错误区域
    if (elements.errorSection) {
        elements.errorSection.style.display = 'block';
    }

    if (elements.errorTitle) {
        elements.errorTitle.textContent = '错误';
    }

    if (elements.errorMessage) {
        elements.errorMessage.textContent = message;
    }
}

/* ============================================================================
   显示进度区域
   ============================================================================ */

function showProgressSection() {
    const elements = getDOMElements();

    // 隐藏错误和结果区域
    if (elements.errorSection) {
        elements.errorSection.style.display = 'none';
    }
    if (elements.resultSection) {
        elements.resultSection.style.display = 'none';
    }

    // 显示进度区域
    if (elements.progressSection) {
        elements.progressSection.style.display = 'block';
    }

    // 重置进度条
    if (elements.progressBarFill) {
        elements.progressBarFill.style.width = '0%';
    }
    if (elements.progressText) {
        elements.progressText.textContent = '0%';
    }
    if (elements.statusMessage) {
        elements.statusMessage.textContent = '正在启动...';
    }
    if (elements.spinner) {
        elements.spinner.style.display = 'block';
    }
}

/* ============================================================================
   重置表单按钮
   ============================================================================ */

function resetFormButtons() {
    const elements = getDOMElements();

    elements.submitBtn.disabled = false;
    elements.apiKey1Input.disabled = false;
    elements.apiKey2Input.disabled = false;
    elements.queryInput.disabled = false;
}

/* ============================================================================
   重置表单
   ============================================================================ */

function resetForm() {
    const elements = getDOMElements();

    // 停止轮询
    stopPolling();
    currentTaskId = null;

    // 清空结果
    if (elements.resultsList) {
        elements.resultsList.innerHTML = '';
    }

    // 隐藏所有分区
    if (elements.progressSection) {
        elements.progressSection.style.display = 'none';
    }
    if (elements.errorSection) {
        elements.errorSection.style.display = 'none';
    }
    if (elements.resultSection) {
        elements.resultSection.style.display = 'none';
    }

    // 显示输入分区
    if (elements.inputSection) {
        elements.inputSection.style.display = 'block';
    }

    // 重置按钮状态
    resetFormButtons();

    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ============================================================================
   下载结果
   ============================================================================ */

function downloadResults() {
    const elements = getDOMElements();

    if (!elements.resultsList) return;

    // 收集结果
    const results = [];
    document.querySelectorAll('.result-item').forEach((item) => {
        const title = item.querySelector('h4')?.textContent || '';
        const url = item.querySelector('.url')?.textContent || '';
        const snippet = item.querySelector('.snippet')?.textContent || '';

        results.push({
            title,
            url,
            snippet
        });
    });

    // 创建数据对象
    const data = {
        query: elements.queryInput.value.trim(),
        timestamp: new Date().toISOString(),
        resultCount: results.length,
        results: results
    };

    // 转换为 JSON 字符串
    const jsonString = JSON.stringify(data, null, 2);

    // 创建 Blob
    const blob = new Blob([jsonString], { type: 'application/json' });

    // 创建下载链接
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `search_results_${Date.now()}.json`;

    // 触发下载
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 清理
    URL.revokeObjectURL(url);
}

/* ============================================================================
   工具函数
   ============================================================================ */

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/* ============================================================================
   错误处理 - 全局异常
   ============================================================================ */

window.addEventListener('error', function (event) {
    console.error('全局错误：', event.error);
});

window.addEventListener('unhandledrejection', function (event) {
    console.error('未处理的 Promise 拒绝：', event.reason);
});
