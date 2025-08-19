direction_mapping = {
    "向上滑动": "UP",
    "向下滑动": "DOWN",
    "向左滑动": "LEFT",
    "向右滑动": "RIGHT",
    "向上滚动": "UP",
    "向下滚动": "DOWN",
    "向左滚动": "LEFT",
    "向右滚动": "RIGHT"
}

# 前者是actions.json 后者是react.json 对应的解析内容
def compare_actions(actions, reacts):
    if (len(actions) != len(reacts)):
        raise Exception(f"[Action and React length mismatch] actions: {len(actions)}, reacts: {len(reacts)}")
    
    for i, (action, react) in enumerate(zip(actions, reacts)):  
        # 比较动作类型（忽略大小写）
        action_type = action.get("type", "").lower()
        react_type = react.get("function").get("name", "").lower()

        if action_type != react_type:
            raise Exception(f"[type mismatch] Action {i+1}: action type {action_type}，react type {react_type}")

        reasoning = react["reasoning"]

        # 展示放弃如reasoning中有滚动滑动，强制让类型变成swipe
        # for desc, expected_direction in direction_mapping.items():
        #     if desc in reasoning:y
        #         if react_type != "swipe":
        #             raise Exception(f"[Swipe action is expected] action {i+1} action: {action}, react: {react}, reasoning: {reasoning}")
        #         break
        
        if(action_type == "swipe"):
            action_direction = action["direction"].upper() if "direction" in action else None

        if(react_type == "swipe"):
            # parameters 内的字段可能不是 direction，而是taget啥的
            if "parameters" not in react["function"] or "direction" not in react["function"]["parameters"]:
                raise Exception(f"[Swipe action missing parameters] React {i+1}: {react}")
            
            react_direction = react["function"]["parameters"]["direction"]

            if(action_direction != react_direction):
                raise Exception(f"[direction mismatch] Action {i+1}: action_direction: {action_direction}, react_direction: {react_direction}")

            flag = False
            for desc, expected_direction in direction_mapping.items():
                if desc in reasoning:
                    if react_direction == expected_direction:
                        flag = True
                        break
                    else:
                        raise Exception(f"[Swipe reasoning direction mismatch] Action {i+1}: action_direction: {action_direction}, react: {react}")
            if not flag:
                raise Exception(f"[Swipe reasoning hasn't direction description] Action {i+1}: action_direction: {action_direction}, react: {react}")