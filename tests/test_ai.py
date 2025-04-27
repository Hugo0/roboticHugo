"""Tests for the ai module."""

import pytest
from unittest.mock import MagicMock  # For creating mock objects/responses

# We need to tell Python where to find the src directory for imports
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Now import the module/functions we want to test
# Imports should work correctly after installing the package
# Try importing directly from the modules within src
import ai
import config

# --- Tests for sanitize_ai_response ---


@pytest.mark.parametrize(
    "input_text, expected_output",
    [
        ("Hello world", "Hello world"),  # Basic case
        (
            "  Leading and trailing spaces  ",
            "Leading and trailing spaces",
        ),  # Whitespace
        ('"Quoted string" ', "Quoted string"),  # Double quotes
        ("'Single quoted'", "Single quoted"),  # Single quotes
        ("`Backticks`", "Backticks"),  # Backticks
        ('   `Combined "quotes"`  ', 'Combined "quotes"'),  # Mixed
        ("", None),  # Empty input -> None
        ("   ", None),  # Whitespace only -> None
        (None, ""),  # None input -> Empty string (or adjust expectation if needed)
        (123, ""),  # Non-string input
        ("A" * 300, "A" * 277 + "..."),  # Too long
        ("Short", "Short"),  # Short enough
    ],
)
def test_sanitize_ai_response(input_text, expected_output):
    """Tests various scenarios for sanitize_ai_response."""
    assert ai.sanitize_ai_response(input_text) == expected_output


# --- Tests for generate_smart_tweet (using mocking) ---


def test_generate_smart_tweet_success(mocker):
    """Tests generate_smart_tweet successful path with mocked OpenAI client."""
    # 1. Arrange: Create a mock OpenAI client and response
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = ' "This is a raw response from AI." \n'
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    # Configure the mock client's method to return the mock response
    mock_openai_client.chat.completions.create.return_value = mock_response

    # 2. Act: Call the function with the mock client
    result = ai.generate_smart_tweet(mock_openai_client)

    # 3. Assert:
    # Check that the create method was called once
    mock_openai_client.chat.completions.create.assert_called_once()
    # Check the result is the sanitized version of the mock message content
    assert result == "This is a raw response from AI."

    # Optional: Assert specific arguments passed to the mocked method
    call_args, call_kwargs = mock_openai_client.chat.completions.create.call_args
    assert call_kwargs["model"] == config.OPENAI_MODEL
    assert (
        call_kwargs["max_completion_tokens"] == 70
    )  # Check if config matches expectation
    assert isinstance(call_kwargs["messages"], list)
    assert len(call_kwargs["messages"]) == 2
    assert call_kwargs["messages"][0]["role"] == "system"


def test_generate_smart_tweet_empty_response(mocker):
    """Tests generate_smart_tweet when AI returns empty/whitespace."""
    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "   ` ` \n"  # Empty after stripping
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_openai_client.chat.completions.create.return_value = mock_response

    result = ai.generate_smart_tweet(mock_openai_client)

    assert result is None  # Expect None if sanitization results in empty
    mock_openai_client.chat.completions.create.assert_called_once()


def test_generate_smart_tweet_api_error(mocker):
    """Tests generate_smart_tweet when the OpenAI API call raises an exception."""
    mock_openai_client = MagicMock()
    # Configure the mock to raise an exception when called
    mock_openai_client.chat.completions.create.side_effect = Exception(
        "Simulated API Error"
    )

    result = ai.generate_smart_tweet(mock_openai_client)

    assert result is None  # Expect None on API error
    mock_openai_client.chat.completions.create.assert_called_once()


def test_generate_smart_tweet_no_client():
    """Tests calling generate_smart_tweet with no client."""
    result = ai.generate_smart_tweet(None)
    assert result is None


# Add more tests as needed, e.g., for different sanitization edge cases or API response structures.
