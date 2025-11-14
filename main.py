import argparse
import sys
from typing import List, Dict


def test_model(user_text: str) -> int:
    try:
        # Lazy import to ensure .env is loaded by client
        from controller.llm_client import VolcClient, build_empathy_system_prompt  # type: ignore
        system_prompt = build_empathy_system_prompt()
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text or "你好，我有点紧张不安。"},
        ]
        client = VolcClient()
        reply = client.chat(messages)
        print("=== Model Response ===")
        print(reply)
        return 0
    except Exception as e:
        print("[Model Test Failed]", str(e))
        return 2


def serve(host: str, port: int, reload: bool = False) -> int:
    try:
        import uvicorn  # type: ignore
        # 'run.py' exposes FastAPI app as 'app'
        uvicorn.run("run:app", host=host, port=port, reload=reload)
        return 0
    except Exception as e:
        print("[Serve Failed]", str(e))
        return 3


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Analyze launcher: serve API or test model")
    sub = parser.add_subparsers(dest="cmd", required=False)

    p_test = sub.add_parser("test-model", help="Call LLM once using .env config")
    p_test.add_argument("text", nargs="?", default="你好，我有点焦虑，想倾诉一下。")

    p_serve = sub.add_parser("serve", help="Start FastAPI server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=5173)
    p_serve.add_argument("--reload", action="store_true")

    args = parser.parse_args(argv)
    # 默认无参数时即启动服务
    if not args.cmd:
        return serve("127.0.0.1", 5173, False)
    if args.cmd == "test-model":
        return test_model(args.text)
    elif args.cmd == "serve":
        return serve(args.host, args.port, args.reload)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))