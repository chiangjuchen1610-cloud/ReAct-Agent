import ast
import inspect
import os
import re
from string import Template
from typing import List, Callable, Tuple

import click
from dotenv import load_dotenv
from google import genai  # 新增：引入 Google SDK
import platform

from prompt_template import react_system_prompt_template

# 新增：啟動時自動讀取 .env 檔案，獲取金鑰
load_dotenv()


class ReActAgent:
    def __init__(self, tools: List[Callable], model: str, project_directory: str):
        self.tools = { func.__name__: func for func in tools }
        self.model = model
        self.project_directory = project_directory
        # 替換為 Google Client，並明確指定讀取環境變數中的金鑰
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def run(self, user_input: str):
        messages = [
            {"role": "system", "content": self.render_system_prompt(react_system_prompt_template)},
            {"role": "user", "content": f"<question>{user_input}</question>"}
        ]

        while True:

            # 请求模型
            content = self.call_model(messages)

            # 检测 Thought
            thought_match = re.search(r"<thought>(.*?)</thought>", content, re.DOTALL)
            if thought_match:
                thought = thought_match.group(1)
                print(f"\n\n💭 Thought: {thought}")

            # 检测模型是否输出 Final Answer，如果是的话，直接返回
            if "<final_answer>" in content:
                final_answer = re.search(r"<final_answer>(.*?)</final_answer>", content, re.DOTALL)
                return final_answer.group(1)

            # 检测 Action
            action_match = re.search(r"<action>(.*?)</action>", content, re.DOTALL)
            if not action_match:
                raise RuntimeError("模型未输出 <action>")
            action = action_match.group(1)
            tool_name, args = self.parse_action(action)

            print(f"\n\n🔧 Action: {tool_name}({', '.join(args)})")
            # 只有终端命令才需要询问用户，其他的工具直接执行
            should_continue = input(f"\n\n是否继续？（Y/N）") if tool_name == "run_terminal_command" else "y"
            if should_continue.lower() != 'y':
                print("\n\n操作已取消。")
                return "操作被用户取消"

            try:
                observation = self.tools[tool_name](*args)
            except Exception as e:
                observation = f"工具执行错误：{str(e)}"
            print(f"\n\n🔍 Observation：{observation}")
            obs_msg = f"<observation>{observation}</observation>"
            messages.append({"role": "user", "content": obs_msg})


    def get_tool_list(self) -> str:
        """生成工具列表字符串，包含函数签名和简要说明"""
        tool_descriptions = []
        for func in self.tools.values():
            name = func.__name__
            signature = str(inspect.signature(func))
            doc = inspect.getdoc(func)
            tool_descriptions.append(f"- {name}{signature}: {doc}")
        return "\n".join(tool_descriptions)

    def render_system_prompt(self, system_prompt_template: str) -> str:
        """渲染系统提示模板，替换变量"""
        tool_list = self.get_tool_list()
        file_list = ", ".join(
            os.path.abspath(os.path.join(self.project_directory, f))
            for f in os.listdir(self.project_directory)
        )
        return Template(system_prompt_template).substitute(
            operating_system=self.get_operating_system_name(),
            tool_list=tool_list,
            file_list=file_list
        )

    @staticmethod
    def get_api_key() -> str:
        """Load the API key from an environment variable."""
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("未找到 OPENROUTER_API_KEY 环境变量，请在 .env 文件中设置。")
        return api_key

    def call_model(self, messages):
        print("\n\n正在请求模型，请稍等...")
        
        # 1. 建立翻譯陣列：將 OpenAI 的 messages 轉換為 Gemini 格式
        #OpenAI 和 Gemini 在對話紀錄的格式與「角色命名」上有所不同，所以第一步必須先進行翻譯。
        #OpenAI 的角色 (Roles) 通常有： user (使用者)、assistant (AI 助理)、system (系統提示詞)。
        #Gemini 的角色通常有： user (使用者)、model (AI 模型)。
        system_prompt = None
        gemini_contents = []
        for msg in messages:
            role = msg["role"]
            
            # 1. 抽離 System Role：只要遇到 system 就存到變數，並跳過不放入對話歷史
            if role == "system":
                system_prompt = msg["content"]
                continue

            # 角色名稱對應轉換
            #程式碼透過一個迴圈 for msg in messages: 檢查每一條歷史訊息：
            #如果遇到 assistant，就自動把它改成 Gemini 看得懂的 model。
            if role == "assistant":
                role = "model" 

            #最後，把這些轉換好的角色和文字內容，打包成 Gemini SDK 專用的物件格式 genai.types.Content，並存入 gemini_contents 陣列中。 
            gemini_contents.append(
                genai.types.Content(
                    role=role,
                    parts=[genai.types.Part.from_text(text=msg["content"])]
                )
            )

            #第一層：抓出純文字 text=msg["content"]
            #這是最核心的資料，也就是原本 OpenAI 歷史紀錄裡，人類或 AI 真正說出來的「一句話」。
            #第二層：變成「部件」 genai.types.Part.from_text(...) 
            #因為 Gemini 非常強大，可以同時看懂文字、圖片、影片（這叫多模態），所以它規定所有傳給它的東西，都要先變成一個個的「部件 (Part)」。這行程式碼就是把剛剛的純文字，包裝成一個「文字部件」。
            #(註：外面的中括號 [] 代表這是一個清單，因為有時候一句話可能同時包含「文字部件」加「圖片部件」)。
            #第三層：貼上身分標籤 genai.types.Content(role=role, parts=...)
            #把剛剛包好的部件拿來，貼上這句話是誰說的標籤（role，也就是我們前一步轉換好的 user 或 model）。這兩樣東西合在一起，就正式成為了一個 Gemini 看得懂的完整對話框 (Content)。
            #第四層：排隊等發車 gemini_contents.append(...)
            #最後，append 的功能就是把這個組裝好的對話框，加到 gemini_contents 這個車廂（陣列）的最後面。
        
        # 2. 呼叫 Gemini 模型
        response = self.client.models.generate_content(
            model=self.model,
            contents=gemini_contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt  # 將抽出來的規則灌進這裡
            )
        )
        
        #self.client.models.generate_content(...) (發送請求)
        #這是向 Google 伺服器下達的指令。意思是：「嘿，客戶端（Client），請幫我呼叫模型（models）來生成內容（generate_content）！」這就像是你把寫好的信交給郵局的櫃檯人員，請他們幫你送出。
        #model=self.model (指定大腦)
        #Gemini 有很多不同的版本（例如：比較聰明的 Pro 版、比較快速的 Flash 版）。這行程式碼是在告訴系統，這次任務要具體指定哪一顆「AI 大腦」來幫我們回答。
        #contents=gemini_contents (附上對話紀錄)
        #這就是把我們在上一個步驟裡，辛苦打包好、翻譯好的那一整串對話紀錄（gemini_contents），全部交給 AI。這樣 AI 才能看到聊天的「前因後果」，而不是只看懂最後一句話。
        #response = ... (接收包裹)
        #當 AI 收到訊息、思考完畢，並回傳結果後，這一段程式碼的開頭 response = 就會負責把這份剛出爐的熱騰騰回覆給「接住」，並暫存到名叫 response 的箱子（變數）裡，好讓後面的程式碼可以把裡面的文字拿出來用。

        # 3. 提取純文字回應
        content = response.text

        #content = response.text (拆包裹拿信)
        #當上一步的 Gemini 伺服器回傳結果（response）時，它其實寄來了一個「大包裹」。這個包裹裡除了 AI 寫的文字，還塞了一堆系統資訊（例如：有沒有觸犯安全機制、總共消耗了多少運算資源等）。
        #但我們的主程式不需要知道這麼多，它只想知道 AI 到底說了什麼。所以 .text 這個動作，就是直接把包裹拆開，只拿出裡面那張寫著純文字的信紙，並把它暫存在叫做 content（內容）的變數裡。

        # 4. 將回應以原本的 OpenAI 格式存回，維持系統相容性
        messages.append({"role": "assistant", "content": content})

        #messages.append(...) (穿上 OpenAI 的制服)
        #這行是這整個轉接器（Adapter）能完美運作的最關鍵一步。
        #{"role": "assistant", "content": content}：因為主程式是為 OpenAI 設計的，它只認得叫做 assistant (助理) 的角色。所以我們在這裡把剛剛拿到的純文字信件，重新套上 OpenAI 規定的「制服」（一個 Python 字典格式）。
        #messages.append(...)：把穿好制服的這句話，歸檔到 messages 這個對話紀錄本的最後一頁。
        #為什麼要這樣做？ 因為這樣一來，下次你要再跟 AI 聊天並附上歷史紀錄時，主程式看這本紀錄本，會覺得：「嗯，格式完全正確，這都是我們家 assistant 說的話。」它完全不會察覺剛剛其實是 Gemini 在背後代工的！

        return content
        #return content (交件給主程式)
        #對話紀錄存好之後，最後一步就是把這段純文字（content）正式回傳（return）給呼叫這段程式碼的源頭。這樣你的前端網頁、APP 或終端機，就能把這段文字顯示出來給使用者看了。

    def parse_action(self, code_str: str) -> Tuple[str, List[str]]:
        match = re.match(r'(\w+)\((.*)\)', code_str, re.DOTALL)
        if not match:
            raise ValueError("Invalid function call syntax")

        func_name = match.group(1)
        args_str = match.group(2).strip()

        # 手动解析参数，特别处理包含多行内容的字符串
        args = []
        current_arg = ""
        in_string = False
        string_char = None
        i = 0
        paren_depth = 0
        
        while i < len(args_str):
            char = args_str[i]
            
            if not in_string:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    current_arg += char
                elif char == '(':
                    paren_depth += 1
                    current_arg += char
                elif char == ')':
                    paren_depth -= 1
                    current_arg += char
                elif char == ',' and paren_depth == 0:
                    # 遇到顶层逗号，结束当前参数
                    args.append(self._parse_single_arg(current_arg.strip()))
                    current_arg = ""
                else:
                    current_arg += char
            else:
                current_arg += char
                if char == string_char and (i == 0 or args_str[i-1] != '\\'):
                    in_string = False
                    string_char = None
            
            i += 1
        
        # 添加最后一个参数
        if current_arg.strip():
            args.append(self._parse_single_arg(current_arg.strip()))
        
        return func_name, args
    
    def _parse_single_arg(self, arg_str: str):
        """解析单个参数"""
        arg_str = arg_str.strip()
        
        # 如果是字符串字面量
        if (arg_str.startswith('"') and arg_str.endswith('"')) or \
           (arg_str.startswith("'") and arg_str.endswith("'")):
            # 移除外层引号并处理转义字符
            inner_str = arg_str[1:-1]
            # 处理常见的转义字符
            inner_str = inner_str.replace('\\"', '"').replace("\\'", "'")
            inner_str = inner_str.replace('\\n', '\n').replace('\\t', '\t')
            inner_str = inner_str.replace('\\r', '\r').replace('\\\\', '\\')
            return inner_str
        
        # 尝试使用 ast.literal_eval 解析其他类型
        try:
            return ast.literal_eval(arg_str)
        except (SyntaxError, ValueError):
            # 如果解析失败，返回原始字符串
            return arg_str

    def get_operating_system_name(self):
        os_map = {
            "Darwin": "macOS",
            "Windows": "Windows",
            "Linux": "Linux"
        }

        return os_map.get(platform.system(), "Unknown")


def read_file(file_path):
    """用于读取文件内容"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def write_to_file(file_path, content):
    """将指定内容写入指定文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content.replace("\\n", "\n"))
    return "写入成功"

def run_terminal_command(command):
    """用于执行终端命令"""
    import subprocess
    run_result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return "执行成功" if run_result.returncode == 0 else run_result.stderr

@click.command()
@click.argument('project_directory',
                type=click.Path(exists=True, file_okay=False, dir_okay=True))
def main(project_directory):
    project_dir = os.path.abspath(project_directory)

    tools = [read_file, write_to_file, run_terminal_command]
    agent = ReActAgent(tools=tools, model="gemini-3.5-flash", project_directory=project_dir)

    task = input("请输入任务：")

    final_answer = agent.run(task)

    print(f"\n\n✅ Final Answer：{final_answer}")

if __name__ == "__main__":
    main()
