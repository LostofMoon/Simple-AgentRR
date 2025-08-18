## 定义动作空间
1. **CLICK [x,y]**: The user clicked on the screen at the position [x,y]. The origin [0,0] is at the top-left corner of the screen, x is the horizontal coordinate, and y is the vertical coordinate. Both x and y are relative coordinates, ranging from 0 to 1000. For example, [500,500] is the center of the screen, and [1000,1000] is the bottom-right corner of the screen.
2. **INPUT `<text>`**: The user typed the text `<text>` using the keyboard. The text can contain characters in any language. The action only happens when the user has already clicked on a search bar or a text input field, and the keyboard is activated.
3. **SWIPE [x1,y1] to [x2,y2]**: The user swiped from the position [x1,y1] to the position [x2,y2]. The meaning of x1, y1, x2, and y2 is the same as in the CLICK action.
4. **DONE**: The user has successfully completed the assigned task. This action indicates that all required objectives have been accomplished and no further interaction is needed.
5. **wait***: Wait to ad, load and redirect

## 1.收集数据
通过人工/自动收集工具，收集每个action前的手机截图，并记录每个action的信息，并汇总到一个actions.json文件中。action格式如下：
{{
    "app_name": str
    "task_description": ["The description of the task list."],
    "action_count": "The count of the actions.",
    "actions": [
        {{
            "type": "The type of the action",
            "parameters": "etc.",  
        }},
        {{
            "type": "click",
            "position_x": "x-coordinate of click",
            "position_y": "y-coordinate of click action",
            "bounds": "the bound of the clicked element",
        }},
        {{
            "type": "swipe",
            "press_position_x": "x-coordinate of press",
            "press_position_y": "y-coordinate of press",
            "release_position_x": "x-coordinate of release",
            "release_position_y": "y-coordinate of release",
            "direction": "The direction of the user's swipe gesture. UP: swipe finger upward to scroll content up and reveal content below. DOWN: swipe finger downward to scroll content down and reveal content above. LEFT: swipe finger leftward to scroll content left. RIGHT: swipe finger rightward to scroll content right."
        }},
        {{
            "type": "input",
            "text": "The text to input",
        }},
        {{
            "type": "done"
        }},
        {{
            "type": "wait"
        }},
    ]
}}

## 2.数据标注
根据actions.json，在截图上做出对应的视觉标注
- The user's action at each time step is annotated at the top of the matched screenshot in **red font**.
Auxiliary information is also annotated in the screenshots:
- For CLICK actions, the exact position of the action is annotated with a **red circle** in the screenshot.
- For SWIPE actions, there is a **red arrow** pointing from the starting position to the ending position in the screenshot.
2. 将所有highlighted的截图和actions.json中的任务描述，一起发给强大算力的大模型，让它给出react.json
[
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "click",
            "parameters": {
                "target_element": "click的highlevel描述"
            }
        }
    },
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "swipe",
            "parameters": {
                "direction": "UP, DOWN, LEFT, RIGHT"
            }
        }
    },
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "input",
            "parameters": {
                "text": "input的内容"
            }
        }
    },
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "done",
            "parameters": {}
        }
    },
    {
        "reasoning": "选择这个function type（action type）的原因",
        "function": {
            "name": "wait",
            "parameters": {}
        }
    }
]

## 3.训练集生成

### decider模型
entry粒度为每一个action
@dataclass
class AlpacaImageEntry:
    instruction: str
    output: str
    images: List[str]
    input: str = ""
    
in：actions' history, task description, current img
out：react.json中一条对应的实例，如下
{
    "reasoning": "选择这个function type（action type）的原因",
    "function": {
        "name": "click, input, swipe, done, wait",
        "parameters": {
            "target_element": "click的highlevel描述",
            "direction": "UP, DOWN, LEFT, RIGHT",
                "text": "input的内容"
        }
    }
}

### grounder模型
type1:
in：target element's description 和 reasoning
out：bounds box [x1, x2, y1, y2]
type2:
in：target element's description 和 reasoning
out：coordinates [x, y]

## 4.使用
### 先将任务描述发给planner 1B，让它做任务拆分，拆分出 <app, app_package, single_task_description>
### 以<app, app_package, single_task_description>为单位，反复调用decider 7B模型，直到给出done动作
### 若decider 7B模型给出的动作为click，调用grounder 3B模型给出点击位置定位

## 问题
1. 升腾真的不好用
2. 收集阶段：reasoning标注不准确（比如有些有默认值的情况和一些corner case需要定制，比如input框 日期选择 默认值） 
3. 收集阶段：bbox不准确，xml乱写以及orc拉的不准确（解决方法是直接删掉，因为点击坐标一定是准确的，我们grounder有两种数据类型，如果给huawei 直接人工拉框）
4. 跷跷板（某个版本没有问题，但是后续出现）
5. corner case：日期选择，向上滑动，无法正确判断当前月份（reset 代码层）
6. dataset：长轨迹（后续动作可能遗忘，提前done。加大后续动作的权重，多复制几份，）
7. dataset：需要基于图而不是基于历史，这边采用dpo的错位训练方式（history和screenshot的index错位，此时让它基于图片index的action而不是此时history对应的index）
8. 暂时无back action，目前正在设计构建