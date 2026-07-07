from OSA.WORKSPACE_GENERATOR import (
    WorkspaceGenerator,
)



def test_workspace_generator():


    generator = WorkspaceGenerator()


    workspace = generator.create(

        customer_id="filmstudio",

        system_name="AI5R FILM OS",

        modules=[

            "STORY_AGENT",

            "PRODUCTION_WORKFLOW",

            "MARKETING_AGENT"

        ]

    )


    assert (
        workspace.system_name
        ==
        "AI5R FILM OS"
    )


    assert (
        workspace.url
        ==
        "filmstudio.osa-system.com"
    )


    assert len(
        workspace.modules
    ) == 3
