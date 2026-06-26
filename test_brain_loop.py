"""Test the agent loop itself with a STUBBED Claude (no API key needed).

Proves the wiring end-to-end: a scripted tool_use turn actually executes the
Sabre tool against the live mock, the result is threaded back, and a final
text turn is returned. Only the LLM is faked; the tool path is real.

    python test_brain_loop.py
"""
import os
import threading
from http.server import HTTPServer

PORT = 8093
os.environ["SABRE_BASE"] = f"http://localhost:{PORT}"

import mock_sabre
import agent_brain


class Blk:
    def __init__(self, type, **kw):
        self.type = type
        self.__dict__.update(kw)


class Resp:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, scripted):
        self.scripted, self.i, self.seen = scripted, 0, []

    def create(self, **kw):
        self.seen.append(list(kw["messages"]))    # snapshot (messages is mutated in place)
        r = self.scripted[self.i]
        self.i += 1
        return r


class FakeClient:
    def __init__(self, scripted):
        self.messages = FakeMessages(scripted)


def main():
    srv = HTTPServer(("127.0.0.1", PORT), mock_sabre.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    # Scripted Claude: turn 1 calls get_booking, turn 2 speaks the answer.
    fake = FakeClient([
        Resp([Blk("tool_use", name="get_booking",
                  input={"confirmationId": "BQAUZG"}, id="tu_1")], "tool_use"),
        Resp([Blk("text", text="Found it — Max Power's trip is confirmed.")], "end_turn"),
    ])

    reply, messages, tools = agent_brain.handle_query("look up booking BQAUZG", client=fake)

    assert tools == ["get_booking"], tools
    assert reply == "Found it — Max Power's trip is confirmed.", reply

    # The tool_result fed back to "Claude" must carry the REAL booking from the mock.
    tool_result_msg = fake.messages.seen[1][-1]        # 2nd call's last message
    payload = tool_result_msg["content"][0]["content"]  # the tool_result string
    assert "POWER" in payload and "LH" in payload, payload[:200]

    srv.shutdown()
    print("brain-loop test ok: tool_use -> real Sabre call -> result threaded -> reply")


if __name__ == "__main__":
    main()
