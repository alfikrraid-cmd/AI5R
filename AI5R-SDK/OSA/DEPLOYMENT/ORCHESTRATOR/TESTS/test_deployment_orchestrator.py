from OSA.DEPLOYMENT.ORCHESTRATOR import (
    DeploymentOrchestrator,
)



def test_deployment_orchestrator():


    orchestrator = DeploymentOrchestrator()


    plan = orchestrator.create_plan(

        system_name="AI5R FILM OS",

        mode="CUSTOMER_SERVER",

        domain="film.company.com"

    )


    assert (
        plan.system_name
        ==
        "AI5R FILM OS"
    )


    assert (
        plan.deployment_mode
        ==
        "CUSTOMER_SERVER"
    )


    assert (
        plan.domain
        ==
        "film.company.com"
    )
