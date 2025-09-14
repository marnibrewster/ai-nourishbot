import gradio as gr
from src.crew import NourishBotRecipeCrew

def format_recipe_output(final_output):
    """
    Formats the recipe output into a table-based Markdown format.
    
    :param final_output: The output from the NourishBotRecipe workflow.
    :return: Formatted output as a Markdown string.
    """
    output = "## 🍽 Recipe Ideas\n\n"
    recipes = []

    # Check if final_output directly contains recipes
    if "recipes" in final_output:
        recipes = final_output["recipes"]
    else:
        # Fallback: try to extract from nested task output
        recipe_task_output = final_output.get("recipe_suggestion_task")
        if recipe_task_output and hasattr(recipe_task_output, "json_dict") and recipe_task_output.json_dict:
            recipes = recipe_task_output.json_dict.get("recipes", [])
    
    if recipes:
        for idx, recipe in enumerate(recipes, 1):
            output += f"### {idx}. {recipe['title']}\n\n"
            
            # Create a table for ingredients
            output += "**Ingredients:**\n"
            output += "| Ingredient |\n"
            output += "|------------|\n"
            for ingredient in recipe['ingredients']:
                output += f"| {ingredient} |\n"
            output += "\n"
            
            # Display instructions and calorie estimate
            output += f"**Instructions:**\n{recipe['instructions']}\n\n"
            output += f"**Calorie Estimate:** {recipe['calorie_estimate']} kcal\n\n"
            output += "---\n\n"
    else:
        output += "No recipes could be generated."
    
    return output



def analyze_food(image, dietary_restrictions, progress=gr.Progress(track_tqdm=True)):
    """
    Wrapper function for the Gradio interface.
    
    :param image: Uploaded image (PIL format)
    :param dietary_restrictions: Dietary restriction as a string (e.g., "vegan")    
    :return: Result from the NourishBot workflow.
    """
    
    image.save("uploaded_image.jpg")  # Save the uploaded image temporarily
    image_path = "uploaded_image.jpg"

    inputs = {
        'uploaded_image': image_path,
        'dietary_restrictions': dietary_restrictions,
    }
    
    # Initialize the appropriate crew instance    
    crew_instance = NourishBotRecipeCrew(
        image_data=image_path,
        dietary_restrictions=dietary_restrictions
    )

    # Run the crew workflow and get the result
    crew_obj = crew_instance.crew()
    # final_output = crew_obj.kickoff(inputs=inputs)
    raw = crew_obj.kickoff(inputs=inputs)

    # final_output = final_output.to_dict()
    
    try:
        data = raw.to_dict()
    except AttributeError:
        data = raw

    # If it's a JSON string, load it:
    if isinstance(data, str):
        import json
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            pass
    
    recipe_markdown = format_recipe_output(data)
    return recipe_markdown
    
# Define custom CSS for styling
css = """
.title {
    font-size: 1.5em !important; 
    text-align: center !important;
    color: #FFD700; 
}

.text {
    text-align: center;
}
"""

js = """
function createGradioAnimation() {
    var container = document.createElement('div');
    container.id = 'gradio-animation';
    container.style.fontSize = '2em';
    container.style.fontWeight = 'bold';
    container.style.textAlign = 'center';
    container.style.marginBottom = '20px';
    container.style.color = '#eba93f';

    var text = 'Welcome to your AI NourishBot!';
    for (var i = 0; i < text.length; i++) {
        (function(i){
            setTimeout(function(){
                var letter = document.createElement('span');
                letter.style.opacity = '0';
                letter.style.transition = 'opacity 0.1s';
                letter.innerText = text[i];

                container.appendChild(letter);

                setTimeout(function() {
                    letter.style.opacity = '0.9';
                }, 50);
            }, i * 250);
        })(i);
    }

    var gradioContainer = document.querySelector('.gradio-container');
    gradioContainer.insertBefore(container, gradioContainer.firstChild);

    return 'Animation created';
}
"""
# Use a theme and custom CSS with Blocks
with gr.Blocks(theme=gr.themes.Citrus(), css=css, js=js) as demo:
    gr.Markdown("# How it works", elem_classes="title")
    gr.Markdown("Upload an image of your fridge content, enter your dietary restriction (if you have any!) then click 'Analyze' to get recipe ideas.", elem_classes="text")
    gr.Markdown("You can also select one of the examples provided to autofill the input sections and click 'Analyze' right away!", elem_classes="text")

    with gr.Row():
        with gr.Column(scale=1, min_width=400):
            gr.Markdown("## Inputs", elem_classes="title")
            image_input = gr.Image(type="pil", label="Upload Image")
            dietary_input = gr.Textbox(label="Dietary Restrictions (optional)", placeholder="e.g., vegan")            
            submit_btn = gr.Button("Analyze")
        
        with gr.Column(scale=2, min_width=600):
            # Place Examples directly under the Analyze button
            gr.Examples(
                examples=[
                    ["examples/food-1.jpg", "vegan", "recipe"],                    
                    ["examples/food-3.jpg", "keto", "recipe"],
                ],
                inputs=[image_input, dietary_input],
                label="Try an Example: Select one of the examples below to autofil the input section then click Analyze"
                # No function or outputs provided, so it only autofills inputs
            )
            gr.Markdown("## Results will appear here...", elem_classes="title")            
            result_display = gr.Markdown(
                "<div style='border: 1px solid #ccc; "
                "padding: 1rem; text-align: center; "
                "color: #666;'>No results yet</div>",
                height=500
            )

    submit_btn.click(
        fn=analyze_food,
        inputs=[image_input, dietary_input],
        outputs=result_display
    )

# Launch the Gradio interface
if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=5000)