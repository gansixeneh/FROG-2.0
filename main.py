# main.py
import sys
import os
sys.path.append(os.path.abspath("."))  # 👈 adds your project root to PYTHONPATH

from orchestrator.ensemble_orchestrator_tool import EnsembleOrchestratorTool

orchestrator = EnsembleOrchestratorTool()

question = "Who is the president of Indonesia in 2024?"
response = orchestrator.run(question)

if isinstance(response, dict):
    print("\n🧾 Final Answer:")
    print(response["answer"])
    print("\n📄 SPARQL:")
    print(response["sparql"])
    print("\n🔎 Raw Results:")
    print(response["raw_result"])
else:
    print("\n⚠️ Failed to answer question:")
    print(response)
