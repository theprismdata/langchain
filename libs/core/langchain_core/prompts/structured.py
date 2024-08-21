from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Type,
    Union,
)

from langchain_core._api.beta_decorator import beta
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts.chat import (
    BaseChatPromptTemplate,
    BaseMessagePromptTemplate,
    ChatPromptTemplate,
    MessageLikeRepresentation,
    MessagesPlaceholder,
    _convert_to_message,
)
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables.base import (
    Other,
    Runnable,
    RunnableSequence,
    RunnableSerializable,
)


@beta()
class StructuredPrompt(ChatPromptTemplate):
    """Structured prompt template for a language model."""

    schema_: Union[Dict, Type[BaseModel]]
    """Schema for the structured prompt."""
    structured_output_kwargs: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def get_lc_namespace(cls) -> List[str]:
        """Get the namespace of the langchain object.

        For example, if the class is `langchain.llms.openai.OpenAI`, then the
        namespace is ["langchain", "llms", "openai"]
        """
        return cls.__module__.split(".")

    @classmethod
    def from_messages_and_schema(
        cls,
        messages: Sequence[MessageLikeRepresentation],
        schema: Union[Dict, Type[BaseModel]],
        **kwargs: Any,
    ) -> ChatPromptTemplate:
        """Create a chat prompt template from a variety of message formats.

        Examples:

            Instantiation from a list of message templates:

            .. code-block:: python

                class OutputSchema(BaseModel):
                    name: str
                    value: int

                template = ChatPromptTemplate.from_messages(
                    [
                        ("human", "Hello, how are you?"),
                        ("ai", "I'm doing well, thanks!"),
                        ("human", "That's good to hear."),
                    ],
                    OutputSchema,
                )

        Args:
            messages: sequence of message representations.
                  A message can be represented using the following formats:
                  (1) BaseMessagePromptTemplate, (2) BaseMessage, (3) 2-tuple of
                  (message type, template); e.g., ("human", "{user_input}"),
                  (4) 2-tuple of (message class, template), (5) a string which is
                  shorthand for ("human", template); e.g., "{user_input}"
            schema: a dictionary representation of function call, or a Pydantic model.
            kwargs: Any additional kwargs to pass through to
                ``ChatModel.with_structured_output(schema, **kwargs)``.

        Returns:
            a structured prompt template
        """
        _messages = [_convert_to_message(message) for message in messages]

        # Automatically infer input variables from messages
        input_vars: Set[str] = set()
        partial_vars: Dict[str, Any] = {}
        for _message in _messages:
            if isinstance(_message, MessagesPlaceholder) and _message.optional:
                partial_vars[_message.variable_name] = []
            elif isinstance(
                _message, (BaseChatPromptTemplate, BaseMessagePromptTemplate)
            ):
                input_vars.update(_message.input_variables)

        return cls(
            input_variables=sorted(input_vars),
            messages=_messages,
            partial_variables=partial_vars,
            schema_=schema,
            structured_output_kwargs=kwargs,
        )

    def __or__(
        self,
        other: Union[
            Runnable[Any, Other],
            Callable[[Any], Other],
            Callable[[Iterator[Any]], Iterator[Other]],
            Mapping[str, Union[Runnable[Any, Other], Callable[[Any], Other], Any]],
        ],
    ) -> RunnableSerializable[Dict, Other]:
        if isinstance(other, BaseLanguageModel) or hasattr(
            other, "with_structured_output"
        ):
            try:
                return RunnableSequence(
                    self,
                    other.with_structured_output(
                        self.schema_, **self.structured_output_kwargs
                    ),
                )
            except NotImplementedError as e:
                raise NotImplementedError(
                    "Structured prompts must be piped to a language model that "
                    "implements with_structured_output."
                ) from e
        else:
            raise NotImplementedError(
                "Structured prompts must be piped to a language model that "
                "implements with_structured_output."
            )

    def pipe(
        self,
        *others: Union[Runnable[Any, Other], Callable[[Any], Other]],
        name: Optional[str] = None,
    ) -> RunnableSerializable[Dict, Other]:
        """Pipe the structured prompt to a language model.

        Args:
            others: The language model to pipe the structured prompt to.
            name: The name of the pipeline. Defaults to None.

        Returns:
            A RunnableSequence object.

        Raises:
            NotImplementedError: If the first element of `others`
            is not a language model.
        """
        if (
            others
            and isinstance(others[0], BaseLanguageModel)
            or hasattr(others[0], "with_structured_output")
        ):
            return RunnableSequence(
                self,
                others[0].with_structured_output(
                    self.schema_, **self.structured_output_kwargs
                ),
                *others[1:],
                name=name,
            )
        else:
            raise NotImplementedError(
                "Structured prompts need to be piped to a language model."
            )
