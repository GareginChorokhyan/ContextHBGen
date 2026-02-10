import gradio as gr
from interface_adapters.ui.gradioController import create_demo, CUSTOM_CSS


if __name__ == "__main__":
    demo = create_demo()
    demo = demo.queue(default_concurrency_limit=1)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft()
    )

    