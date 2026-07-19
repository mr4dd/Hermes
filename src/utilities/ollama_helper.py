import ollama

def test_and_prime_model(system_prompt: str, model: str = "llama3.2-vision:11b"):
    local_models = {m.model for m in ollama.list().models}
    if model not in local_models:
        ollama.pull(model)
    
    ollama.chat(
        model=model,
        messages=[
            {
                "role":"system",
                "content":system_prompt
            }
        ])

def query_model_with_image(system_prompt: str, prompt: str, image_path: str, model: str = "llama3.2-vision:11b") -> str:
    
    response = ollama.chat(
        model=model,
        messages=[
            {
                "role":"system",
                "content":system_prompt
            },
            {"role": "user", "content": prompt, "images": [image_path]},
        ],
    )

    output = response.message.content
    return output