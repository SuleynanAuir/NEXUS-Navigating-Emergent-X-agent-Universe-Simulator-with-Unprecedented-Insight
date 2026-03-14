import asyncio
import argparse

from controller import Controller
from utils.deepseek_client import DeepSeekClient
from utils.tavily_client import TavilyClient
from config import settings


async def main():
    parser = argparse.ArgumentParser(description="MARDS - Multi-Agent Reflective Deep Search")
    parser.add_argument("--query", type=str, required=True, help="Research query")
    parser.add_argument("--debate", action="store_true", help="Enable debate agent")
    args = parser.parse_args()

    deepseek = DeepSeekClient() if settings.deepseek_api_key else None
    tavily = TavilyClient()

    controller = Controller(deepseek_client=deepseek, tavily_client=tavily)
    result = await controller.run(args.query, enable_debate=args.debate)

    print("\n" + "=" * 60)
    print("MARDS FINAL REPORT")
    print("=" * 60)
    print(result.synthesis["report_markdown"])
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
