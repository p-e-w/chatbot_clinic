# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023  Philipp Emanuel Weidmann <pew@worldwidemann.com>

import html
from enum import Enum
from random import shuffle

import gradio as gr

from modules import shared
from modules.ui import create_refresh_button, gather_interface_values
from modules.chat import start_new_chat, generate_chat_reply
from modules.utils import gradio, get_available_presets
from modules.presets import load_preset


params = {
    "display_name": "Chatbot Clinic",
    "is_tab": True,
    # Configurable parameters
    "max_bots": 10,
    "enabled_bots": 3,
    "user_name": "You",
    "bot_name": "Bot",
    "greeting": "Hello, my friend. What can I do for you?",
    "bot_identifier_prefix": "Bot",
    "bot_context": (
        "The bot is a personal assistant and answers all questions, and fulfills all"
        " requests, to the best of its ability."
    ),
}


class Step(Enum):
    IDLE = 1
    WAITING_FOR_MESSAGE = 2
    GENERATING = 3
    WAITING_FOR_VOTE = 4


class Bot:
    def __init__(self, identifier, context, parameters):
        self.identifier = identifier
        self.context = context
        self.parameters = parameters
        self.votes = 0


class State:
    def __init__(self):
        self.step = Step.IDLE
        self.bots = []


# Adapted from https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/4afaaf8a020c1df457bcf7250cb1c7f609699fa7/modules/ui_components.py#L88
#
# Extensive modifications were necessary because for reasons I don't understand,
# the `Checkbox` constructor ignores its arguments. Why the original code works in
# stable-diffusion-webui is a mystery to me.
class InputAccordion(gr.Checkbox):
    def __init__(self, value, **kwargs):
        kwargs_checkbox = {
            **kwargs,
            "visible": False,
        }
        super().__init__(value, **kwargs_checkbox)

        kwargs_accordion = {
            **kwargs,
            "open": value,
            "label": kwargs.get("label", "Accordion"),
            "elem_classes": ["chatbot-clinic-input-accordion"],
        }
        self.accordion = gr.Accordion(**kwargs_accordion)

    def __enter__(self):
        self.accordion.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.accordion.__exit__(exc_type, exc_val, exc_tb)

    def get_block_name(self):
        return "checkbox"


def custom_js():
    return """
    // Adapted from https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/4afaaf8a020c1df457bcf7250cb1c7f609699fa7/javascript/ui.js#L315
    function updateInput(target) {
        const event = new Event("input", {bubbles: true});
        Object.defineProperty(event, "target", {value: target});
        target.dispatchEvent(event);
    }

    // Adapted from https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/4afaaf8a020c1df457bcf7250cb1c7f609699fa7/javascript/inputAccordion.js
    const observerAccordionOpen = new MutationObserver(mutations => {
        for (const mutationRecord of mutations) {
            const labelWrap = mutationRecord.target;
            const accordion = labelWrap.parentNode;
            const checkbox = accordion.previousElementSibling.querySelector("input");

            checkbox.checked = labelWrap.classList.contains("open");
            updateInput(checkbox);
        }
    });

    for (const accordion of document.querySelectorAll(".chatbot-clinic-input-accordion")) {
        const labelWrap = accordion.querySelector(".label-wrap");
        observerAccordionOpen.observe(labelWrap, {attributes: true, attributeFilter: ["class"]});
    }
    """


focus_message_textbox_js = """
function focusMessageTextbox() {
    setTimeout(() => {
        document.querySelector("#chatbot-clinic-message textarea").focus();
    }, 1000);
}
"""


scroll_chat_js = """
function scrollChat() {
    element = document.querySelector("#chatbot-clinic-chat .bubble-wrap");
    element.scrollTop = element.scrollHeight;
}
"""


about_markdown = """
# Chatbot Clinic

Science-driven chatbot development.

**Repository:** https://github.com/p-e-w/chatbot_clinic

**Issue tracker:** https://github.com/p-e-w/chatbot_clinic/issues


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
"""


def ui():
    state = gr.State()

    with gr.Tab("Common configuration"):
        gr.Markdown(
            "These settings must be the same for all chatbots in order to keep the"
            " prompt logically consistent. When you are satisfied with their values,"
            " proceed to the next tab to configure the individual bots."
        )
        user_name = gr.Textbox(
            params["user_name"],
            label="Your name",
            info="The name that is used to identify the user in the prompt.",
        )
        bot_name = gr.Textbox(
            params["bot_name"],
            label="Chatbot name",
            info="The name that is used to identify the chatbot in the prompt.",
        )
        greeting = gr.Textbox(
            params["greeting"],
            label="Greeting",
            info=(
                "The initial message sent by the chatbot to set the stage for the"
                " conversation."
            ),
            lines=10,
        )

    with gr.Tab("Chatbot configuration"):
        gr.Markdown(
            "Configure as many chatbots as you like (up to a limit controlled by the"
            " `max_bots` global setting). When you are done, proceed to the next tab to"
            " start the chat."
        )

        bot_enabled = []
        bot_identifier = []
        bot_context = []
        bot_preset = []

        for i in range(params["max_bots"]):
            with InputAccordion(
                i < params["enabled_bots"], label=f"Chatbot {i+1}"
            ) as bot_enabled_i:
                bot_enabled.append(bot_enabled_i)
                bot_identifier.append(
                    gr.Textbox(
                        f"{params['bot_identifier_prefix']} {i+1}",
                        label="Identifier",
                        info=(
                            "The name that is used to identify the chatbot in the user"
                            " interface. To set the name that is used to identify the"
                            ' chatbot in the prompt, go to the "Common configuration"'
                            " tab."
                        ),
                    )
                )
                bot_context.append(
                    gr.Textbox(
                        params["bot_context"],
                        label="Context",
                        info=(
                            "The persistent context for the chatbot, prepended to the"
                            " truncated chat history in the prompt. Commonly used to"
                            ' control the "personality" of the bot.'
                        ),
                        lines=10,
                    )
                )

                with gr.Row():
                    bot_preset.append(
                        gr.Dropdown(
                            choices=get_available_presets(),
                            value=shared.settings["preset"],
                            label="Generation parameters",
                            info=(
                                "The set of parameter values controlling the behavior"
                                " of the language model during text generation. To add"
                                ' or edit parameter presets, go to the "Parameters" tab'
                                " in the main UI."
                            ),
                        )
                    )
                    create_refresh_button(
                        bot_preset[-1],
                        lambda: None,
                        lambda: {"choices": get_available_presets()},
                        "refresh-button",
                        interactive=not shared.args.multi_user,
                    )

    with gr.Tab("Chat", elem_id="chatbot-clinic-chat-tab"):
        with gr.Row():
            with gr.Column(scale=5):
                gr.Markdown(
                    "Click the button to start/stop the chat. Switch to the"
                    ' "Statistics" tab at any time to see an analysis of the data'
                    ' collected so far. Note that <span style="color:'
                    ' yellow;">configuration changes have no effect while a chat is'
                    " running.</span> You must stop and restart the chat to apply them."
                    ' Note also that <span style="color: red;">stopping a chat deletes'
                    " all messages and statistics.</span> They are not saved to disk"
                    " and must be manually copied if they are needed later."
                )
            with gr.Column(scale=1, min_width=100):
                start_chat = gr.Button("Start chat", variant="primary")
                stop_chat = gr.Button("Stop chat", variant="stop", visible=False)

        chatbot = gr.Chatbot(
            show_label=False, visible=False, elem_id="chatbot-clinic-chat"
        )

        with gr.Row():
            with gr.Column(scale=10):
                message = gr.Textbox(
                    placeholder="Message",
                    show_label=False,
                    container=False,
                    visible=False,
                    elem_id="chatbot-clinic-message",
                )
            with gr.Column(scale=1, min_width=60):
                send = gr.Button("Send", variant="primary", visible=False)

    with gr.Tab("Statistics"):
        no_statistics = gr.Markdown(
            "No preference statistics have been collected yet. To see statistics, start"
            " a chat and vote on at least one set of bot replies."
        )

        warning = gr.Markdown(
            '<span style="color: yellow;">Careful when interpreting these'
            " numbers:</span> The percentage of times a specific bot was preferred is"
            " **not** the same thing as, or even an approximation of, the likelihood"
            " that it is the best bot, in some rigorous sense. Calculating that"
            " likelihood is a very complex task that requires making several"
            " (potentially false) assumptions about the underlying probability"
            ' distributions.\n\nA good practical approach to finding the "best bot" is'
            " to go through a number of message/response cycles and keep watching these"
            " statistics. When the ranking remains stable over several consecutive"
            " messages, there is a good chance that the best bot has been identified.",
            visible=False,
        )

        ranking_title = gr.Markdown("## Ranking", visible=False)
        ranking = gr.Label(
            show_label=False,
            container=False,
            visible=False,
            elem_id="chatbot-clinic-ranking",
        )

        table_title = gr.Markdown("## Raw data", visible=False)
        table = gr.Dataframe(
            headers=["Identifier", "Votes", "Vote percentage"],
            datatype=["str", "number", "number"],
            visible=False,
        )

    with gr.Tab("About"):
        gr.Markdown(about_markdown)

    def process_history(history):
        return [[user if user else None, bot] for user, bot in history["visible"]]

    def initialize_state(*args):
        new_state = State()
        new_state.interface_values = gather_interface_values(*args)
        return new_state

    def do_start_chat(data):
        new_state = data[state]

        new_state.step = Step.WAITING_FOR_MESSAGE

        new_state.interface_values["name1"] = data[user_name]
        new_state.interface_values["name2"] = data[bot_name]
        new_state.interface_values["greeting"] = data[greeting]
        new_state.interface_values["history"] = start_new_chat(
            new_state.interface_values
        )

        for enabled, identifier, context, preset in zip(
            bot_enabled, bot_identifier, bot_context, bot_preset
        ):
            if data[enabled]:
                new_state.bots.append(
                    Bot(data[identifier], data[context], load_preset(data[preset]))
                )

        new_state.bot_order = list(range(len(new_state.bots)))

        return {
            state: new_state,
            start_chat: gr.update(visible=False),
            stop_chat: gr.update(visible=True),
            chatbot: gr.update(
                value=process_history(new_state.interface_values["history"]),
                visible=True,
                elem_classes=[],
            ),
            message: gr.update(value="", interactive=True, visible=True),
            send: gr.update(interactive=True, visible=True),
        }

    def do_stop_chat():
        return {
            start_chat: gr.update(visible=True),
            stop_chat: gr.update(visible=False),
            chatbot: gr.update(visible=False),
            message: gr.update(visible=False),
            send: gr.update(visible=False),
            no_statistics: gr.update(visible=True),
            warning: gr.update(visible=False),
            ranking_title: gr.update(visible=False),
            ranking: gr.update(visible=False),
            table_title: gr.update(visible=False),
            table: gr.update(visible=False),
        }

    def do_send(data):
        new_state = data[state]

        new_state.step = Step.GENERATING

        yield {
            state: new_state,
            message: gr.update(value="", interactive=False),
            send: gr.update(interactive=False),
        }

        shuffle(new_state.bot_order)

        visible_history = process_history(new_state.interface_values["history"])

        for reply_count, bot_index in enumerate(new_state.bot_order, start=1):
            bot = new_state.bots[bot_index]

            new_state.interface_values["context"] = bot.context
            new_state.interface_values.update(bot.parameters)

            visible_history.append([None, None])

            for history in generate_chat_reply(
                data[message], new_state.interface_values
            ):
                user_message, bot_message = history["visible"][-1]

                if reply_count == 1 and user_message:
                    visible_history[-1][0] = user_message

                visible_history[-1][1] = bot_message

                yield {
                    chatbot: gr.update(
                        value=visible_history,
                        elem_classes=[
                            "chatbot-clinic-generating",
                            f"chatbot-clinic-replies-{reply_count}",
                        ],
                    ),
                }

            bot.reply = {
                "visible": history["visible"][-1],
                "internal": history["internal"][-1],
            }

        new_state.step = Step.WAITING_FOR_VOTE

        yield {
            state: new_state,
            chatbot: gr.update(
                elem_classes=[
                    "chatbot-clinic-waiting-for-vote",
                    f"chatbot-clinic-replies-{reply_count}",
                ]
            ),
        }

    def do_select(event: gr.SelectData, data):
        new_state = data[state]

        history = new_state.interface_values["history"]

        index, sender = event.index

        if (
            new_state.step == Step.WAITING_FOR_VOTE
            and sender == 1
            and index >= len(history["visible"])
        ):
            bot_index = index - len(history["visible"])
            bot = new_state.bots[new_state.bot_order[bot_index]]

            new_state.step = Step.WAITING_FOR_MESSAGE

            user_message, bot_message = bot.reply["visible"]

            history["visible"].append([
                user_message,
                (
                    "<div"
                    f' class="chatbot-clinic-bot-identifier">{html.escape(bot.identifier)}</div>'
                    f" {bot_message}"
                ),
            ])
            history["internal"].append(bot.reply["internal"])

            bot.votes += 1

            total_votes = sum([bot.votes for bot in new_state.bots])
            ranking_data = {
                bot.identifier: bot.votes / total_votes for bot in new_state.bots
            }
            table_data = [
                [bot.identifier, bot.votes, round(bot.votes / total_votes * 100)]
                for bot in new_state.bots
            ]

            return {
                state: new_state,
                chatbot: gr.update(value=process_history(history), elem_classes=[]),
                message: gr.update(interactive=True),
                send: gr.update(interactive=True),
                no_statistics: gr.update(visible=False),
                warning: gr.update(visible=True),
                ranking_title: gr.update(visible=True),
                ranking: gr.update(value=ranking_data, visible=True),
                table_title: gr.update(visible=True),
                table: gr.update(value=table_data, visible=True),
            }

        return {
            state: new_state,
        }

    start_chat.click(
        initialize_state,
        inputs=gradio(shared.input_elements),
        outputs=state,
        show_progress="hidden",
    ).then(
        do_start_chat,
        inputs={
            state,
            user_name,
            bot_name,
            greeting,
            *bot_enabled,
            *bot_identifier,
            *bot_context,
            *bot_preset,
        },
        outputs=[state, start_chat, stop_chat, chatbot, message, send],
        show_progress="hidden",
    ).then(
        None, _js=focus_message_textbox_js, show_progress="hidden"
    )

    stop_chat.click(
        do_stop_chat,
        inputs=[],
        outputs=[
            start_chat,
            stop_chat,
            chatbot,
            message,
            send,
            no_statistics,
            warning,
            ranking_title,
            ranking,
            table_title,
            table,
        ],
        show_progress="hidden",
    )

    gr.on(
        triggers=[message.submit, send.click],
        fn=do_send,
        inputs={state, message},
        outputs=[state, chatbot, message, send],
        show_progress="hidden",
    )

    chatbot.select(
        do_select,
        inputs={state},
        outputs=[
            state,
            chatbot,
            message,
            send,
            no_statistics,
            warning,
            ranking_title,
            ranking,
            table_title,
            table,
        ],
        show_progress="hidden",
    ).then(None, _js=focus_message_textbox_js, show_progress="hidden")

    chatbot.change(None, _js=scroll_chat_js, show_progress="hidden")


def custom_css():
    # The purpose of this CSS sorcery is to display instructions inside
    # the chatbot component, even though the component doesn't support
    # such custom elements. Dynamically added classes (see Python code above)
    # are used to orchestrate this system.
    generated_css = f"""
    {", ".join([
        f".chatbot-clinic-replies-{i+1} .bot-row:nth-last-child({i+1})"
        for i in range(params["max_bots"])
    ])} {{
        display: block !important;
    }}

    {", ".join([
        f".chatbot-clinic-replies-{i+1} .bot-row:nth-last-child(-n+{i})"
        for i in range(1, params["max_bots"])
    ])} {{
        display: block !important;
        margin-top: -1em;
    }}

    {", ".join([
        f".chatbot-clinic-replies-{i+1} .bot-row:nth-last-child({i+1})::before"
        for i in range(params["max_bots"])
    ])} {{
        content: 'These are the replies generated by the configured chatbots, in random order:';
        color: khaki;
        display: block;
        margin-bottom: 1em;
    }}
    """

    return """
    .chatbot-clinic-input-accordion .label-wrap.open > :first-child::after {
        content: 'Enabled';
        color: lime;
        font-weight: bold;
        font-size: smaller;
        margin-left: 1em;
    }

    #chatbot-clinic-chat-tab .generating {
        display: none !important;
    }

    #chatbot-clinic-chat {
        height: calc(100dvh - 300px) !important;
    }

    /*
    Workaround for a strange Gradio bug that inserts a blank user message
    at the start of the chat while the component is being updated.
    */
    #chatbot-clinic-chat .user-row:first-child {
        display: none;
    }

    .chatbot-clinic-bot-identifier {
        color: aqua;
        font-weight: bold;
    }

    #chatbot-clinic-ranking h2 {
        display: none;
    }

    .chatbot-clinic-waiting-for-vote .bot-row:last-child::after {
        content: 'To proceed, click on the reply you like best.';
        color: lightgreen;
        display: block;
        margin-top: 1em;
    }
    """ + generated_css
