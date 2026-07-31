"""What the agent receives decides whether it answers or reaches for a tool."""

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from knowli.infrastructure.llm.openai import OpenAICompatibleModel


class RecordingChat(GenericFakeChatModel):
    """A fake chat model that keeps the messages the agent handed it."""

    seen: list = []

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        RecordingChat.seen = list(messages)
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def test_the_question_reaches_the_model_as_a_question_not_as_data():
    """Wrapped in a JSON payload the question reads as data, and the model answers
    from the claims instead of calling a tool that would have the real answer."""
    RecordingChat.seen = []
    chat = RecordingChat(messages=iter([AIMessage("Tuesdays.")]))
    model = OpenAICompatibleModel(chat_model=chat)

    list(
        model.stream_answer(
            "When do we deploy?",
            [{"id": "claim-1", "statement": "Deploy on Tuesdays."}],
            thread_id="thread-1",
        )
    )

    system, human = RecordingChat.seen
    assert isinstance(human, HumanMessage)
    assert human.content == "When do we deploy?"
    assert isinstance(system, SystemMessage)
    assert "Deploy on Tuesdays." in system.content
