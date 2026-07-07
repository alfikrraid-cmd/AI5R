from BUSINESS_VERTICALS.UMKM_OS.MEMORY import (
    UMKMMemorySystem,
    BusinessMemory,
)



def test_umkm_memory():


    memory = UMKMMemorySystem()


    result = memory.store(

        BusinessMemory(

            memory_id="EXP-001",

            category="MARKETING",

            experience={

                "campaign":
                "Ramadan",

                "result":
                "sales increased"

            }

        )

    )


    assert result["status"] == "STORED"


    saved = memory.recall(
        "EXP-001"
    )


    assert saved.category == "MARKETING"


    learning = memory.learn()


    assert learning["status"] == "LEARNING"
