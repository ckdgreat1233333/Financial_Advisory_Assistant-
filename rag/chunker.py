import re


class PolicyChunker:

    def chunk(self, policy_text: str) -> list[str]:

        pattern = r"(?=Section\s+\d+\s*-)"

        chunks = re.split(pattern, policy_text)

        chunks = [
            chunk.strip()
            for chunk in chunks
            if chunk.strip().startswith("Section")
        ]

        return chunks