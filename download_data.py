from biomni.agent.a1 import A1
import os

try:
    A1(
        llm='gpt-4.1-mini',
        api_key=os.environ['HATZ_API_KEY'],
        base_url='https://ai.hatz.ai/v1',
        timeout_seconds=600,
        use_tool_retriever=True,
        path='/app/data'
    )
except Exception as e:
    print('A1 init raised (expected for build-only download):', e)

print('Data lake download complete')
