# Chatbot Clinic

Developing virtual characters for use with large language models can be
a process that more closely resembles alchemy than engineering. Endless
tinkering around with character descriptions, followed by unscientific
"tests" where a few chat messages are exchanged with the bot, and at last
a semi-educated guess on whether the change has been an improvement or not.

Chatbot Clinic is an extension for
[text-generation-webui](https://github.com/oobabooga/text-generation-webui)
that automates and formalizes that process. It brings science to the art
of creating chatbots.


## How it works

### :one: Configure as many chatbots as you like

Each one can have its own context and generation parameters. This allows
you to comparatively evaluate both character descriptions and parameter
presets, or any combination thereof.

![Step 1](https://github.com/p-e-w/chatbot_clinic/assets/2702526/cd6a0495-44ac-4eec-924b-622476b9fee7)


### :two: Chat with all of them simultaneously

When you send a message to the chat, you receive a reply from each of the
configured bots. Clicking on your preferred reply continues the chat with
that reply, and records this as a vote for the bot that wrote it.

The replies are presented in random order and without identifying the bots,
to avoid any potential source of bias and ensure that your vote is based
solely on the content of the replies.

![Step 2](https://github.com/p-e-w/chatbot_clinic/assets/2702526/1a3e85a4-d563-4a01-a5b7-1f8e52ef4218)


### :three: See which one you voted for the most

Numbers talk, bullshit walks! The statistics view gives you a breakdown of
how many votes you gave to each bot's replies, so you can make an informed
decision on which bot is "best", without having to rely on any hunches.

![Step 3](https://github.com/p-e-w/chatbot_clinic/assets/2702526/ff66b718-7c3e-4fad-a11a-bd19865da782)


## Installation

Installing Chatbot Clinic follows the standard process for installing
[text-generation-webui](https://github.com/oobabooga/text-generation-webui)
extensions, namely:

1. Install and run text-generation-webui.
2. Navigate to the **Session** tab.
3. Paste the URL `https://github.com/p-e-w/chatbot_clinic` into the textbox
   labeled **Install or update an extension** and press Enter.
4. Restart text-generation-webui.
5. In the **Session** tab, check the entry `chatbot_clinic` under
   **Available extensions**, then click **Save UI defaults to settings.yaml**,
   then click **Apply flags/extensions and restart**.
6. Make sure you have installed and loaded a language model.
7. Navigate to the **Chatbot Clinic** tab to use the extension.


## License

Copyright &copy; 2023  Philipp Emanuel Weidmann (<pew@worldwidemann.com>)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

**By contributing to this project, you agree to release your
contributions under the same license.**
