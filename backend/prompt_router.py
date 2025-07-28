def get_prompt(user_role, topic, context):
    if user_role == "student":
        return f"You are a friendly tutor. Help the student learn about {topic}. Use the following material: {context}"
    elif user_role == "teacher":
        return f"You are an expert education assistant. Summarize the lesson on {topic} and generate 5 quiz questions. Use this content: {context}"
    elif user_role == "parent":
        return f"You are a progress tracker. Summarize the student's learning journey on the topic '{topic}' in simple language. Use: {context}"
    else:
        return "Unrecognized role. Cannot generate a prompt."
