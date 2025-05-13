from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *
import re
from .forward import ForwardMessage 

# 注册插件
@register(name="Msg2Forward", 
          description="合并长消息转发和标签清理功能 | 当回复超过长度阈值时使用合并转发，并自动清理think等标签", 
          version="0.2", 
          author="sheetung")
class Msg2Forward(BasePlugin):
    
    # 默认配置（可在配置文件中覆盖）
    default_config = {
        'threshold': 200,          # 触发转发的消息长度阈值
        'enable_tag_clean': True,  # 是否启用标签清理功能
        'sender_info': {
            'user_id': '1000000',  # 转发消息的发送者ID
            'nickname': 'bot'      # 转发消息的发送者昵称
        },
        'prompt_template': "长消息播报",
        'summary_template': "长消息播报转发",
        'forward_mode': 'single'  # 转发模式：single/multi
    }

    def __init__(self, host: APIHost):
        # 初始化转发器和合并配置
        self.forwarder = ForwardMessage("127.0.0.1", 3000)
        self.config = self.default_config # 合并默认配置和用户配置
        
    def _clean_message_tags(self, msg: str) -> str:
        """
        清理消息中的特殊标签（增强版）
        移除所有指定标签及其内容，并优化排版
        """
        if not self.config['enable_tag_clean']:
            return msg
            
        # 清理完整标签对
        for tag in ['think', 'details', 'summary', 'thinking']:
            msg = re.sub(
                rf'<{tag}\b[^>]*>[\s\S]*?</{tag}>', 
                '', 
                msg, 
                flags=re.DOTALL | re.IGNORECASE
            )
        
        # 清理残留标签和内容
        msg = re.sub(
            r'<(think|details|summary|thinking)\b[^>]*>[\s\S]*?(?=<|$)', 
            '', 
            msg, 
            flags=re.IGNORECASE
        )
        
        # 清理结束标签
        msg = re.sub(
            r'</(think|details|summary|thinking)>', 
            '', 
            msg, 
            flags=re.IGNORECASE
        )
        
        # 优化排版
        # msg = re.sub(r'\n{3,}', '\n\n', msg)          # 合并多个空行
        # msg = re.sub(r'(?<!\n)\n(?!\n)', ' ', msg)    # 单换行转空格
        return msg.strip()

    @handler(NormalMessageResponded)
    async def handle_message_response(self, ctx: EventContext):
        original_msg = ctx.event.response_text
        launcher_id = ctx.event.launcher_id
        sender_id = ctx.event.sender_id
        
        # Step 1: 清理消息标签
        processed_msg = self._clean_message_tags(original_msg)
        
        # 如果清理后消息为空则跳过
        if not processed_msg:
            self.ap.logger.warning("[Msg2Forward] 处理后的消息为空，跳过处理")
            return
            
        # 记录处理结果
        self.ap.logger.debug(f"[Msg2Forward] 原始消息长度: {len(original_msg)} | 处理后长度: {len(processed_msg)}")
        
        # Step 2: 判断是否需要转发
        need_forward = (
            len(processed_msg) >= self.config['threshold'] 
            and sender_id != launcher_id  # 排除私聊
        )
        
        if need_forward:
            # 准备转发消息
            forward_messages = self.forwarder.convert_to_forward(processed_msg)
            await self.forwarder.send_forward(
                launcher_id=str(launcher_id),
                messages=forward_messages,
                prompt=self.config['prompt_template'],
                # summary=self.config['summary_template'].format(count=len(processed_msg)),
                summary=self.config['summary_template'],
                source="bot消息",
                **self.config['sender_info'],
                mode=self.config['forward_mode']
            )
            ctx.prevent_default()  # 阻止默认回复
        else:
            # 如果消息被修改过但不需要转发，则更新回复内容
            if processed_msg != original_msg:
                # ctx.event.response_text = processed_msg
                ctx.add_return("reply", [processed_msg])
                self.ap.logger.info("[Msg2Forward] 已清理标签消息但未达转发阈值")

    def __del__(self):
        pass
