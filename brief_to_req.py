import ollama

MODEL = "qwen3:8b"


def read_brief(path="brief.txt"):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def ask_qwen(brief_text):
    prompt = (
        "Read the following requirements brief and produce the software "
        "requirements for it.\n\n"
        f"{brief_text}"
    )
    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user", 
                "content": prompt
            }
        ],
    )
    return response["message"]["content"]


if __name__ == "__main__":
    brief = read_brief()
    requirements = ask_qwen(brief)

    print(requirements)

    with open("robot_requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements)

