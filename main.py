from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *
import re
from .forward import ForwardMessage 

# 注册插件
@register(name="Msg2Forward", description="...", version="0.1", author="sheetung")
class Msg2Forward(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        # pass
        self.forwarder = ForwardMessage("127.0.0.1", 3000)
        self.forward_config = {
           'threshold': 200,
            'sender_info': {
                'user_id': '1000000',
                'nickname': 'Lngbot'
            },
            'prompt_template': "长消息播报",
            'summary_template': "长消息播报转发"
        }

    @handler(NormalMessageResponded)
    async def group_normal_message_received(self, ctx: EventContext):
        msg = ctx.event.response_text

        self.ap.logger.info(f"[Msg2Forward] 收到消息 | 长度: {len(msg)}")
        
        if len(msg) >= self.forward_config['threshold']:

            forward_messages = self.forwarder.convert_to_forward(msg)
            await self.forwarder.send_forward(
                launcher_id=str(ctx.event.launcher_id),
                messages=forward_messages,
                prompt=self.forward_config['prompt_template'],
                summary=self.forward_config['summary_template'].format(count=len(msg)),
                source="Langbot消息",
                **self.forward_config['sender_info'],
                mode='multi'
            )
            ctx.prevent_default()  # 防止后续处理
            return
            # event.add_return('reply', msg)
        

    # 插件卸载时触发
    def __del__(self):
        pass