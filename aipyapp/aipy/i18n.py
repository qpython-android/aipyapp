#!/usr/bin/env python
# -*- coding: utf-8 -*-

import locale

MESSAGES = {
    'zh': {
        'start_instruction': '开始处理指令',
        'start_execute': '开始执行代码块',
        'execute_result': '执行结果',
        'start_feedback': '开始反馈结果',
        'end_instruction': '结束处理指令',
        'no_context': '未找到上下文信息',
        'upload_success': '文章上传成功',
        'upload_failed': '上传失败 (状态码: {})',
        'reset_warning': '严重警告：这将重新初始化❗❗❗',
        'reset_confirm': '如果你确定要继续，请输入 y',
        'llm_response': '响应',
        'env_description': '环境变量名称和意义',
        'description': '描述',
        'unknown_format': '不支持的文件格式',
        'ask_for_packages': '申请安装第三方包',
        'agree_packages': '如果同意，请输入',
        'ask_for_env': '申请获取环境变量 {}，用途',
        'env_exist': '环境变量 {} 存在，返回给代码使用',
        'input_env': '未找到环境变量 {}，请输入',
        'call_failed': '调用失败',
        'think': '思考',
        'publish_disabled': "当前环境不支持发布",
        'auto_confirm': '自动确认',
        'packages_exist': '申请的第三方包已经安装',
        'thinking': '正在绞尽脑汁思考中，请稍等6-60秒',
        'no_available_llm': '没有可用的 LLM，请检查配置文件',
        'banner1_python': "请用 ai('任务') 输入需要 AI 处理的任务 (输入 ai.use(llm) 切换下述 LLM：",
        'banner1': "请输入需要 AI 处理的任务 (输入 /use <下述 LLM> 切换)",
        'default': '默认',
        'enabled': '已启用',
        'ai_mode_enter': '进入 AI 模式，开始处理任务，输入 Ctrl+d 或 /done 结束任务',
        'ai_mode_exit': "[退出 AI 模式]",
        'ai_mode_unknown_command': "[AI 模式] 未知命令",
        'Task Summary': '任务总结',
        'Round': '轮次',
        'Time(s)': '时间(秒)',
        'In Tokens': '输入令牌数',
        'Out Tokens': '输出令牌数',
        'Total Tokens': '总令牌数',
        'sending_task': '正在向 {} 下达任务',
        'error_loading_config': "加载配置时出错: {}",
        'config_file_error': "请检查配置文件路径和格式。",
        'config_not_loaded': "配置尚未加载。",
        'llm_config_not_found': "缺少 'llm' 配置。",
        'trustoken_register_instruction': (
            "当前环境缺少配置文件，请注册一个trustoken账号，可以使用免费赠送的API账号。\n"
            "浏览器打开 https://api.trustoken.ai/register ， 进行账号注册。\n"
            "注册后进行登录，访问页面顶部的“令牌”页面，或者点击这个地址：https://api.trustoken.ai/token \n"
            "点击“复制”按钮，复制令牌到剪贴板。在下面进行粘贴。\n"
            "另外，也可以选择退出，然后手动编辑配置文件 {}，配置自己已有的其他大模型令牌"
        ),
        'pgpttoken_register_instruction': (
            "当前环境缺少配置文件，需要注册PGPT账号获取试用Token。\n"
            "请按以下步骤操作：\n"
            "1. 访问 https://user.pgpt.cloud/ 完成账号注册\n"
            "2. 登录后创建App（选择Deepseek或者OpenAI）。操作详见文档 https://docs.pgpt.cloud/\n"
            "3. 获取API Key并复制到剪贴板，然后在此粘贴\n"
            "您也可以选择退出，然后手动编辑配置文件 {} 来配置已有的其他大模型Token"
        ),
        'prompt_token_input': "请粘贴令牌并按 Enter 键 (输入 'exit' 退出): ",
        'exit_token_prompt': "退出令牌输入流程。",
        'no_token_detected': "未检测到令牌输入。",
        'invalid_token': "输入的令牌不合法，请确保令牌正确，格式为‘sk-xxxxxx……’，或输入 'exit' 退出。",
        'token_saved': "令牌已保存到 {}",
        'token_save_error': "保存令牌时出错: {}",
        'not usable': "不可用",
        'permission_denied_error': "无权限创建目录: {}",
        'error_creating_config_dir': "创建配置目录时出错: {}",
        'migrate_config': "成功的将旧版本配置迁移到 {}",
        'binding_request_sent': "绑定请求发送成功。\n请求ID: {}\n\n>>> 请在已认证设备的浏览器中打开以下链接以批准:\n>>> {}\n\n(该链接将在{}秒后过期)",
        'scan_qr_code': "或者扫描下方二维码：",
        'qr_code_display_failed': "(无法显示二维码: {})\n",
        'coordinator_request_error': "连接到协调服务器或请求时出错: {}",
        'unexpected_request_error': "请求过程中发生意外错误: {}",
        'waiting_for_approval': "等待批准...",
        'current_status': "当前状态: {}...",
        'binding_expired': "\n绑定请求已过期。",
        'unknown_status': "\n收到未知状态: {}",
        'coordinator_polling_error': "轮询协调服务器时出错: {}",
        'unexpected_polling_error': "轮询过程中发生意外错误: {}",
        'polling_cancelled': "\n用户取消了轮询。",
        'polling_timeout': "\n轮询超时。",
        'start_binding_process': "当前环境缺少必需的配置文件，开始进行配置初始化流程，与trustoken账号绑定即可自动获取配置...",
        'binding_success': "\n绑定流程已成功完成。",
        'binding_failed': "\n绑定流程失败或未完成。",
        'binding_request_failed': "\n绑定请求发起失败。",
        'The operation completed successfully': "操作成功完成",
        'Execution was interrupted by the user': "操作被用户中断",
        'Initial mission': "最初任务",
        'Code execution result feedback': "代码执行结果反馈",
    },
    'en': {
        'start_instruction': 'Start processing instruction',
        'start_execute': 'Start executing code block',
        'execute_result': 'Execution result',
        'start_feedback': 'Start sending feedback',
        'end_instruction': 'End processing instruction',
        'no_context': 'No context information found',
        'upload_success': 'Article uploaded successfully',
        'upload_failed': 'Upload failed (status code: {})',
        'reset_warning': 'Severe warning: This will reinitialize❗❗❗',
        'reset_confirm': 'If you are sure to continue, enter y',
        'llm_response': 'reply',
        'env_description': 'Environment variable name and meaning',
        'description': 'Description',
        'unknown_format': 'Unsupported file format',
        'ask_for_packages': 'Request to install third-party packages',
        'agree_packages': 'If you agree, please enter',
        'ask_for_env': 'Request to obtain environment variable {}, purpose',
        'env_exist': 'Environment variable {} exists, returned for code use',
        'input_env': 'Environment variable {} not found, please enter',
        'call_failed': 'Call failed',
        'think': 'Think',
        'publish_disabled': "Current environment does not support publishing",
        'auto_confirm': 'Auto confirm',
        'packages_exist': 'Third-party packages have been installed',
        'thinking': 'is thinking hard, please wait 6-60 seconds',
        'no_available_llm': 'No available LLM, please check the configuration file',
        'banner1_python': "Please use ai('task') to enter the task to be processed by AI (enter ai.use(llm) to switch to the following LLM:",
        'banner1': "Please enter the task to be processed by AI (enter /use <following LLM> to switch)",
        'default': 'Default',
        'enabled': 'Enabled',
        'ai_mode_enter': 'Enter AI mode, start processing tasks, enter Ctrl+d or /done to end the task',
        'ai_mode_exit': "[Exit AI mode]",
        'ai_mode_unknown_command': "[AI mode] Unknown command",
        'Task Summary': 'Task Summary',
        'Round': 'Round',
        'Time(s)': 'Time(s)',
        'In Tokens': 'In Tokens',
        'Out Tokens': 'Out Tokens',
        'Total Tokens': 'Total Tokens',
        'sending_task': 'Sending task to {}',
        'error_loading_config': "Error loading configuration: {}",
        'config_file_error': "Please check the configuration file path and format.",
        'config_not_loaded': "Configuration not loaded.",
        'llm_config_not_found': "Missing 'llm' configuration.",
        'trustoken_register_instruction': (
            "The current environment lacks a configuration file. Please register for a Trustoken account to use the free API token.\n"
            "Open https://api.trustoken.ai/register to register.\n"
            "After registration, log in and visit the 'Token' page at the top, or navigate to: https://api.trustoken.ai/token\n"
            "Click the 'copy' button to copy your token to the clipboard and paste it here.\n"
            "Alternatively, you can exit now, and manually edit the configuration file {} to configure your existing LLM token."
        ),
        'pgpttoken_register_instruction': (
            "The current environment is missing configuration files. You need to register a PGPT account to get trial tokens.\n"
            "Please follow these steps:\n"
            "1. Visit https://user.pgpt.cloud/ to complete account registration\n"
            "2. After logging in, create an App (please select Deepseek or OpenAI). See documentation: https://docs.pgpt.cloud/\n"
            "3. Get your API Key, copy it to clipboard, then paste it here\n"
            "Alternatively, you can exit and manually edit the configuration file {} to set up tokens for other existing LLM models"
        ),
        'prompt_token_input': "Please paste the token and press Enter (type 'exit' to quit): ",
        'exit_token_prompt': "Exiting token input process.",
        'no_token_detected': "No token detected.",
        'invalid_token': "The entered token is invalid. Ensure it starts with 'sk-' followed by the correct characters, or type 'exit' to quit.",
        'token_saved': "Token saved to {}",
        'token_save_error': "Error saving token: {}",
        'not usable': "Not usable",
        'permission_denied_error': "Permission denied to create directory: {}",
        'error_creating_config_dir': "Error creating configuration directory: {}",
        'migrate_config': "Successfully migrated old version configuration to {}",
        'binding_request_sent': "Binding request sent successfully.\nRequest ID: {}\n\n>>> Please open this URL in your browser on an authenticated device to approve:\n>>> {}\n\n(This link expires in {} seconds)",
        'scan_qr_code': "Or scan the QR code below:",
        'qr_code_display_failed': "(Could not display QR code: {})\n",
        'coordinator_request_error': "Error connecting to coordinator or during request: {}",
        'unexpected_request_error': "An unexpected error occurred during request: {}",
        'waiting_for_approval': "Waiting for approval...",
        'current_status': "Current status: {}...",
        'binding_expired': "\nBinding request expired.",
        'unknown_status': "\nUnknown status received: {}",
        'coordinator_polling_error': "Error connecting to coordinator during polling: {}",
        'unexpected_polling_error': "An unexpected error occurred during polling: {}",
        'polling_cancelled': "\nPolling cancelled by user.",
        'polling_timeout': "\nPolling timed out.",
        'start_binding_process': "The current environment lacks the required configuration file. Starting the configuration initialization process to bind with the Trustoken account...",
        'binding_success': "\nBinding process completed successfully.",
        'binding_failed': "\nBinding process failed or was not completed.",
        'binding_request_failed': "\nFailed to initiate binding request.",
        'The operation completed successfully': "The operation completed successfully",
        'Execution was interrupted by the user': "Execution was interrupted by the user",
        'Initial mission': "Initial mission",
        'Code execution result feedback': "Code execution result feedback",

    }
}

__lang__ = 'en'

def set_lang(lang=None):
    global __lang__, MESSAGES
    if lang and lang in MESSAGES:
        __lang__ = lang
        return
    
    language, _ = locale.getlocale()
    if language:
        language = language.lower()
        if language.find('china') >=0 or language.find('chinese') >= 0 or language.find('zh_') >= 0:
            __lang__ = 'zh'

def T(key, *args):
    msg = MESSAGES[__lang__][key]
    return msg.format(*args) if args else msg

set_lang()
