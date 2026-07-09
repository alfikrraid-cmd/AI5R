from FACTORY.ARTIFACTS.template_renderer import TemplateRenderer


def test_template_renderer_replaces_placeholder():
    rendered = TemplateRenderer().render(
        "Hello {{name}}",
        {
            "name": "AI5R",
        },
    )

    assert rendered == "Hello AI5R"


def test_template_renderer_handles_multiple_values():
    rendered = TemplateRenderer().render(
        "{{project_name}} uses {{framework}}",
        {
            "project_name": "Login API",
            "framework": "FastAPI",
        },
    )

    assert rendered == "Login API uses FastAPI"


def test_template_renderer_leaves_unknown_placeholder():
    rendered = TemplateRenderer().render(
        "Hello {{name}} {{unknown}}",
        {
            "name": "AI5R",
        },
    )

    assert rendered == "Hello AI5R {{unknown}}"
