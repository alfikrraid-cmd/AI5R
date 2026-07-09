from FACTORY.PACKS.CONTRACTS.pack_contract import REQUIRED_FIELDS


class FactoryPackValidator:

    def validate(self, contract):

        missing = []

        for field in REQUIRED_FIELDS:

            value = getattr(contract, field)

            if value in (None, "", []):

                missing.append(field)

        if missing:

            raise ValueError(
                f"Factory Pack Contract missing fields: {', '.join(missing)}"
            )

        return True
