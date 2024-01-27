import time, re
from config import config

class OpenAIHelper:
    maxchecks = 240
    lastprompt = ""

    def __init__(self, bot):
        self.bot = bot

    def generate_request(self, message, finish_reason, object):
        return {
            "id": "chatcmpl-6ptKyqKOGXZT6iQnqiXAH8adNLUzD",
            "object": object,
            "created": int(time.time()),
            "model": "gpt-3.5-turbo-0613",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "content": message
                    },
                    "finish_reason": finish_reason
                }
            ]
        }
    
    def format_message(self, messages):
        formatted_messages = []
        char = None
        user = None

        for message in messages:
            role = message.get("role", "Unknown")
            name = message.get("name", "")
            content = message.get("content", "")
    
            char_match = re.search(r"\[Character==(.+?)\]", content)
            user_match = re.search(r"\[User==(.+?)\]", content)
            
            if char_match:
                char = char_match.group(1)
                content = content.replace(char_match.group(0), '')

            if user_match:
                user = user_match.group(1)
                content = content.replace(user_match.group(0), '')
                
            if role == "assistant" and char:
                name = char

            if role == "user" and user:
                name = user
        
            formatted_msg = f"{role if not name else name}: {content}"
            formatted_messages.append(formatted_msg)
        return "\n".join(formatted_messages)
    
    def send_message(self, messages):
        message = self.format_message(messages)
        if ("[ClaudeJB]" in message):
            message = message.replace("[ClaudeJB]", "")
            if (self.lastprompt == message):
                self.bot.delete_latest_message(True)
                time.sleep(1)
                self.bot.delete_latest_message(False)
                self.bot.send_message(config.get("ClaudeJB", "I love it. Continue."))
            else:
                self.bot.clear_context()
                self.lastprompt = message
                self.bot.send_message(message, False)
                self.bot.abort_message()
                time.sleep(0.5)
                self.bot.delete_latest_message()
                time.sleep(1)
                self.bot.send_message(config.get("ClaudeJB", "I love it. Continue."))
        else:
            self.bot.clear_context()
            self.bot.send_message(message)

    def generate_completions(self, messages):
        self.send_message(messages)
        checks = 0
        while checks < self.maxchecks:
            current_message = self.bot.get_latest_message()
            if 'user:' in current_message:
                self.bot.abort_message()
                # Process or truncate message as needed
                current_message = current_message.split('user:')[0].strip()
                return self.generate_request(current_message, "stop", "chat.completion")

            if not self.bot.is_generating():
                # Message generation finished, process the final message
                return self.generate_request(current_message, "stop", "chat.completion")

            checks += 1
            time.sleep(1)

    def generate_completions_stream(self):
        checks = 0
        old_message_length = 0
        aborted_due_to_user = False

        while checks < self.maxchecks:
            time.sleep(1)
            current_message = self.bot.get_latest_message()
            current_message = current_message.rstrip('\n')
            new_message_length = len(current_message)
            new_message = current_message[old_message_length:new_message_length]

            # Find the last whitespace character in the new message
            last_space = max(new_message.rfind(' '), new_message.rfind('\t'), new_message.rfind('\n'))
            if last_space != -1:
                new_message = new_message[:last_space + 1]

            if 'user:' in current_message:
                self.bot.abort_message()
                aborted_due_to_user = True  # Set the flag when aborting
                break

            if not self.bot.is_generating():
                break

            old_message_length += len(new_message)

            if new_message != "":
                yield self.generate_request(new_message, None, "chat.completion.chunk")
            checks += 1

        final_message = current_message[old_message_length:]
        if final_message != "":
            if aborted_due_to_user:
                # If aborted due to "user:", check if there's more text after "user:"
                if 'user:' in final_message:
                    final_message = final_message.split('user:')[0].strip()
                    if final_message != "":
                        yield self.generate_request(final_message, "stop", "chat.completion.chunk")
            else:
                yield self.generate_request(final_message, "stop", "chat.completion.chunk")