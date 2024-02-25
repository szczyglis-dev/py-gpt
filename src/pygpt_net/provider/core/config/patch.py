#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 01:00:00                  #
# ================================================== #

import os

from packaging.version import parse as parse_version, Version


class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version) -> bool:
        """
        Migrate config to current app version

        :param version: current app version
        :return: True if migrated
        """
        data = self.window.core.config.all()
        current = "0.0.0"
        updated = False
        is_old = False

        # get version of config file
        if '__meta__' in data and 'version' in data['__meta__']:
            current = data['__meta__']['version']
        old = parse_version(current)

        # check if config file is older than current app version
        if old < version:

            # mark as older version
            is_old = True

            # < 0.9.1
            if old < parse_version("0.9.1"):
                print("Migrating config from < 0.9.1...")
                keys_to_remove = ['user_id', 'custom']  # not needed anymore
                for key in keys_to_remove:
                    if key in data:
                        del data[key]
                keys_to_add = ['organization_key']
                for key in keys_to_add:
                    if key not in data:
                        data[key] = ""
                updated = True

            # < 0.9.2
            if old < parse_version("0.9.2"):
                print("Migrating config from < 0.9.2...")
                keys_to_remove = ['ui.ctx.min_width',
                                  'ui.ctx.max_width',
                                  'ui.toolbox.min_width',
                                  'ui.toolbox.max_width',
                                  'ui.dialog.settings.width',
                                  'ui.dialog.settings.height',
                                  'ui.chatbox.font.color']
                for key in keys_to_remove:
                    if key in data:
                        del data[key]
                if 'theme' not in data:
                    data['theme'] = "dark_teal"
                updated = True

            # < 0.9.4
            if old < parse_version("0.9.4"):
                print("Migrating config from < 0.9.4...")
                if 'plugins' not in data:
                    data['plugins'] = {}
                if 'plugins_enabled' not in data:
                    data['plugins_enabled'] = {}
                updated = True

            # < 0.9.6
            if old < parse_version("0.9.6"):
                print("Migrating config from < 0.9.6...")
                data['debug'] = True  # enable debug by default
                updated = True

            # < 2.0.0
            if old < parse_version("2.0.0"):
                print("Migrating config from < 2.0.0...")
                data['theme'] = 'dark_teal'  # force, because removed light themes!
                if 'cmd' not in data:
                    data['cmd'] = True
                if 'stream' not in data:
                    data['stream'] = True
                if 'attachments_send_clear' not in data:
                    data['attachments_send_clear'] = True
                if 'assistant' not in data:
                    data['assistant'] = None
                if 'assistant_thread' not in data:
                    data['assistant_thread'] = None
                updated = True

            # < 2.0.1
            if old < parse_version("2.0.1"):
                print("Migrating config from < 2.0.1...")
                if 'send_mode' not in data:
                    data['send_mode'] = 1
                if 'send_shift_enter' in data:
                    del data['send_shift_enter']
                if 'font_size.input' not in data:
                    data['font_size.input'] = 11
                if 'font_size.ctx' not in data:
                    data['font_size.ctx'] = 9
                if 'ctx.auto_summary' not in data:
                    data['ctx.auto_summary'] = True
                if 'ctx.auto_summary.system' not in data:
                    data['ctx.auto_summary.system'] = "You are an expert in conversation summarization"
                if 'ctx.auto_summary.prompt' not in data:
                    data['ctx.auto_summary.prompt'] = "Summarize topic of this conversation in one sentence. Use best " \
                                                      "keywords to describe it. Summary must be in the same language " \
                                                      "as the conversation and it will be used for conversation title " \
                                                      "so it must be EXTREMELY SHORT and concise - use maximum 5 " \
                                                      "words: \n\nUser: {input}\nAI Assistant: {output}"
                updated = True

            # < 2.0.6
            if old < parse_version("2.0.6"):
                print("Migrating config from < 2.0.6...")
                if 'layout.density' not in data:
                    data['layout.density'] = -2
                updated = True

            # < 2.0.8
            if old < parse_version("2.0.8"):
                print("Migrating config from < 2.0.8...")
                if 'plugins' not in data:
                    data['plugins'] = {}
                if 'cmd_web_google' not in data['plugins']:
                    data['plugins']['cmd_web_google'] = {}
                data['plugins']['cmd_web_google'][
                    'prompt_summarize'] = "Summarize the English text in a maximum of 3 " \
                                          "paragraphs, trying to find the most " \
                                          "important content that can help answer the " \
                                          "following question: "
                data['plugins']['cmd_web_google']['chunk_size'] = 100000
                data['plugins']['cmd_web_google']['max_page_content_length'] = 0
                updated = True

            # < 2.0.13
            if old < parse_version("2.0.13"):
                print("Migrating config from < 2.0.13...")
                if 'layout.density' not in data:
                    data['layout.density'] = 0
                else:
                    if data['layout.density'] == -2:
                        data['layout.density'] = 0
                updated = True

            # < 2.0.14
            if old < parse_version("2.0.14"):
                print("Migrating config from < 2.0.14...")
                if 'vision.capture.enabled' not in data:
                    data['vision.capture.enabled'] = True
                if 'vision.capture.auto' not in data:
                    data['vision.capture.auto'] = True
                if 'vision.capture.width' not in data:
                    data['vision.capture.width'] = 800
                if 'vision.capture.height' not in data:
                    data['vision.capture.height'] = 600
                updated = True

            # < 2.0.16
            if old < parse_version("2.0.16"):
                print("Migrating config from < 2.0.16...")
                if 'vision.capture.idx' not in data:
                    data['vision.capture.idx'] = 0
                if 'img_raw' not in data:
                    data['img_raw'] = True
                if 'img_prompt_model' not in data:
                    data['img_prompt_model'] = "gpt-4-1106-preview"
                updated = True

            # < 2.0.19
            if old < parse_version("2.0.19"):
                print("Migrating config from < 2.0.19...")
                if 'img_raw' not in data:
                    data['img_raw'] = True
                if not data['img_raw']:
                    data['img_raw'] = True
                updated = True

            # < 2.0.25
            if old < parse_version("2.0.25"):
                print("Migrating config from < 2.0.25...")
                if 'cmd.prompt' not in data:
                    data['cmd.prompt'] = self.window.core.config.get_base('cmd.prompt')
                if 'img_prompt' not in data:
                    data['img_prompt'] = self.window.core.config.get_base('img_prompt')
                if 'vision.capture.quality' not in data:
                    data['vision.capture.quality'] = 85
                if 'attachments_capture_clear' not in data:
                    data['attachments_capture_clear'] = True
                if 'plugins' not in data:
                    data['plugins'] = {}
                if 'cmd_web_google' not in data['plugins']:
                    data['plugins']['cmd_web_google'] = {}
                data['plugins']['cmd_web_google']['prompt_summarize'] = "Summarize the English text in a maximum of 3 " \
                                                                        "paragraphs, trying to find the most " \
                                                                        "important content that can help answer the " \
                                                                        "following question: "
                updated = True

            # < 2.0.26
            if old < parse_version("2.0.26"):
                print("Migrating config from < 2.0.26...")
                if 'ctx.auto_summary.model' not in data:
                    data['ctx.auto_summary.model'] = 'gpt-3.5-turbo-1106'
                updated = True

            # < 2.0.27
            if old < parse_version("2.0.27"):
                print("Migrating config from < 2.0.27...")
                if 'plugins' not in data:
                    data['plugins'] = {}
                if 'cmd_web_google' not in data['plugins']:
                    data['plugins']['cmd_web_google'] = {}
                data['plugins']['cmd_web_google'][
                    'prompt_summarize'] = "Summarize text in English in a maximum of 3 " \
                                          "paragraphs, trying to find the most " \
                                          "important content that can help answer the " \
                                          "following question: {query}"
                data['cmd.prompt'] = self.window.core.config.get_base('cmd.prompt')  # fix
                updated = True

            # < 2.0.30
            if old < parse_version("2.0.30"):
                print("Migrating config from < 2.0.30...")
                if 'plugins' not in data:
                    data['plugins'] = {}
                if 'audio_openai_whisper' not in data['plugins']:
                    data['plugins']['audio_openai_whisper'] = {}
                data['plugins']['audio_openai_whisper']['timeout'] = 1
                data['plugins']['audio_openai_whisper']['phrase_length'] = 5
                data['plugins']['audio_openai_whisper']['min_energy'] = 2000
                updated = True

            # < 2.0.31
            if old < parse_version("2.0.31"):
                print("Migrating config from < 2.0.31...")
                if 'plugins' not in data:
                    data['plugins'] = {}
                if 'audio_openai_whisper' not in data['plugins']:
                    data['plugins']['audio_openai_whisper'] = {}
                data['plugins']['audio_openai_whisper']['continuous_listen'] = False
                data['plugins']['audio_openai_whisper']['timeout'] = 2
                data['plugins']['audio_openai_whisper']['phrase_length'] = 4
                data['plugins']['audio_openai_whisper']['magic_word_timeout'] = 1
                data['plugins']['audio_openai_whisper']['magic_word_phrase_length'] = 2
                data['plugins']['audio_openai_whisper']['min_energy'] = 1.3
                updated = True

            # < 2.0.34
            if old < parse_version("2.0.34"):
                print("Migrating config from < 2.0.34...")
                if 'lock_modes' not in data:
                    data['lock_modes'] = True
                updated = True

            # < 2.0.37
            if old < parse_version("2.0.37"):
                print("Migrating config from < 2.0.37...")
                if 'font_size.toolbox' not in data:
                    data['font_size.toolbox'] = 12
                updated = True

            # < 2.0.46
            if old < parse_version("2.0.46"):
                print("Migrating config from < 2.0.46...")
                data['cmd'] = False  # disable on default
                updated = True

            # < 2.0.47
            if old < parse_version("2.0.47"):
                print("Migrating config from < 2.0.47...")
                if 'notepad.num' not in data:
                    data['notepad.num'] = 5
                updated = True

            # < 2.0.52
            if old < parse_version("2.0.52"):
                print("Migrating config from < 2.0.52...")
                if 'layout.dpi.scaling' not in data:
                    data['layout.dpi.scaling'] = True
                if 'layout.dpi.factor' not in data:
                    data['layout.dpi.factor'] = 1.0
                updated = True

            # < 2.0.62
            if old < parse_version("2.0.62"):
                print("Migrating config from < 2.0.62...")
                if 'ctx.records.limit' not in data:
                    data['ctx.records.limit'] = 0
                updated = True

            # < 2.0.65
            if old < parse_version("2.0.65"):
                print("Migrating config from < 2.0.65...")
                if 'ctx.search.string' not in data:
                    data['ctx.search.string'] = ""
                updated = True

            # < 2.0.69
            if old < parse_version("2.0.69"):
                print("Migrating config from < 2.0.69...")
                data['img_prompt'] = "Whenever I provide a basic idea or concept for an image, such as 'a picture " \
                                     "of mountains', I want you to ALWAYS translate it into English and expand " \
                                     "and elaborate on this idea. Use your knowledge and creativity to add " \
                                     "details that would make the image more vivid and interesting. This could " \
                                     "include specifying the time of day, weather conditions, surrounding " \
                                     "environment, and any additional elements that could enhance the scene. Your " \
                                     "goal is to create a detailed and descriptive prompt that provides DALL-E " \
                                     "with enough information to generate a rich and visually appealing image. " \
                                     "Remember to maintain the original intent of my request while enriching the " \
                                     "description with your imaginative details."
                data['img_raw'] = False
                data['img_prompt_model'] = "gpt-4-1106-preview"
                updated = True

            # < 2.0.71
            if old < parse_version("2.0.71"):
                print("Migrating config from < 2.0.71...")
                prompt = 'IMAGE GENERATION: Whenever I provide a basic idea or concept for an image, such as \'a picture of ' \
                         'mountains\', I want you to ALWAYS translate it into English and expand and elaborate on this idea. ' \
                         'Use your  knowledge and creativity to add details that would make the image more vivid and ' \
                         'interesting. This could include specifying the time of day, weather conditions, surrounding ' \
                         'environment, and any additional elements that could enhance the scene. Your goal is to create a ' \
                         'detailed and descriptive prompt that provides DALL-E  with enough information to generate a rich ' \
                         'and visually appealing image. Remember to maintain the original  intent of my request while ' \
                         'enriching the description with your imaginative details. HOW TO START IMAGE GENERATION: to start ' \
                         'image generation return to me prepared prompt in JSON format, all in one line,  using following ' \
                         'syntax: ~###~{"cmd": "image", "params": {"query": "your query here"}}~###~. Use ONLY this syntax ' \
                         'and remember to surround JSON string with ~###~.  DO NOT use any other syntax. Use English in the ' \
                         'generated JSON command, but conduct all the remaining parts of the discussion with me in the ' \
                         'language in which I am speaking to you. The image will be generated on my machine  immediately ' \
                         'after the command is issued, allowing us to discuss the photo once it has been created.  Please ' \
                         'engage with me about the photo itself, not only by giving the generate command. '
                if 'openai_dalle' not in data['plugins']:
                    data['plugins']['openai_dalle'] = {}
                    data['plugins']['openai_dalle']['prompt'] = prompt  # fixed prompt

                data['plugins_enabled']['openai_dalle'] = True
                data['plugins_enabled']['openai_vision'] = True

                # deprecate vision and img modes
                if data['mode'] == 'vision' or data['mode'] == 'img':
                    data['mode'] = 'chat'

                updated = True

            # < 2.0.72
            if old < parse_version("2.0.72"):
                print("Migrating config from < 2.0.72...")
                if 'theme.markdown' not in data:
                    data['theme.markdown'] = True
                prompt = 'IMAGE GENERATION: Whenever I provide a basic idea or concept for an image, such as \'a picture of ' \
                         'mountains\', I want you to ALWAYS translate it into English and expand and elaborate on this idea. ' \
                         'Use your  knowledge and creativity to add details that would make the image more vivid and ' \
                         'interesting. This could include specifying the time of day, weather conditions, surrounding ' \
                         'environment, and any additional elements that could enhance the scene. Your goal is to create a ' \
                         'detailed and descriptive prompt that provides DALL-E  with enough information to generate a rich ' \
                         'and visually appealing image. Remember to maintain the original  intent of my request while ' \
                         'enriching the description with your imaginative details. HOW TO START IMAGE GENERATION: to start ' \
                         'image generation return to me prepared prompt in JSON format, all in one line,  using following ' \
                         'syntax: ~###~{"cmd": "image", "params": {"query": "your query here"}}~###~. Use ONLY this syntax ' \
                         'and remember to surround JSON string with ~###~.  DO NOT use any other syntax. Use English in the ' \
                         'generated JSON command, but conduct all the remaining parts of the discussion with me in the ' \
                         'language in which I am speaking to you. The image will be generated on my machine  immediately ' \
                         'after the command is issued, allowing us to discuss the photo once it has been created.  Please ' \
                         'engage with me about the photo itself, not only by giving the generate command. '
                if 'openai_dalle' not in data['plugins']:
                    data['plugins']['openai_dalle'] = {}
                data['plugins']['openai_dalle']['prompt'] = prompt  # fixed prompt
                updated = True

            # < 2.0.75
            if old < parse_version("2.0.75"):
                print("Migrating config from < 2.0.75...")
                if 'updater.check.launch' not in data:
                    data['updater.check.launch'] = True
                if 'updater.check.bg' not in data:
                    data['updater.check.bg'] = False
                updated = True

            # < 2.0.78
            if old < parse_version("2.0.78"):
                print("Migrating config from < 2.0.78...")
                if 'render.plain' not in data:
                    data['render.plain'] = False
                updated = True

            # < 2.0.81
            if old < parse_version("2.0.81"):
                print("Migrating config from < 2.0.81...")
                self.window.core.updater.patch_css('markdown.light.css', True)  # force replace file
                updated = True

            # < 2.0.85
            if old < parse_version("2.0.85"):
                print("Migrating config from < 2.0.85...")
                prompt = "AUTONOMOUS MODE:\n1. You will now enter self-dialogue mode, where you will be conversing with " \
                         "yourself, not with a human.\n2. When you enter self-dialogue mode, remember that you are engaging " \
                         "in a conversation with yourself. Any user input will be considered a reply featuring your previous response.\n" \
                         "3. The objective of this self-conversation is well-defined—focus on achieving it.\n" \
                         "4. Your new message should be a continuation of the last response you generated, essentially replying" \
                         " to yourself and extending it.\n5. After each response, critically evaluate its effectiveness " \
                         "and alignment with the goal. If necessary, refine your approach.\n6. Incorporate self-critique " \
                         "after every response to capitalize on your strengths and address areas needing improvement.\n7. To " \
                         "advance towards the goal, utilize all the strategic thinking and resources at your disposal.\n" \
                         "8. Ensure that the dialogue remains coherent and logical, with each response serving as a stepping " \
                         "stone towards the ultimate objective.\n9. Treat the entire dialogue as a monologue aimed at devising" \
                         " the best possible solution to the problem.\n10. Conclude the self-dialogue upon realizing the " \
                         "goal or reaching a pivotal conclusion that meets the initial criteria.\n11. You are allowed to use " \
                         "any commands and tools without asking for it.\n12. While using commands, always use the correct " \
                         "syntax and never interrupt the command before generating the full instruction.\n13. ALWAYS break " \
                         "down the main task into manageable logical subtasks, systematically addressing and analyzing each" \
                         " one in sequence.\n14. With each subsequent response, make an effort to enhance your previous " \
                         "reply by enriching it with new ideas and do it automatically without asking for it.\n14. Any input " \
                         "that begins with 'user: ' will come from me, and I will be able to provide you with ANY additional " \
                         "commands or goal updates in this manner. The other inputs, not prefixed with 'user: ' will represent" \
                         " your previous responses.\n15. Start by breaking down the task into as many smaller sub-tasks as " \
                         "possible, then proceed to complete each one in sequence.  Next, break down each sub-task into even " \
                         "smaller tasks, carefully and step by step go through all of them until the required goal is fully " \
                         "and correctly achieved.\n"
                if 'self_loop' not in data['plugins']:
                    data['plugins']['self_loop'] = {}
                data['plugins']['self_loop']['prompt'] = prompt  # fixed prompt

                # before fix (from 2.0.72)
                prompt = 'IMAGE GENERATION: Whenever I provide a basic idea or concept for an image, such as \'a picture of ' \
                         'mountains\', I want you to ALWAYS translate it into English and expand and elaborate on this idea. ' \
                         'Use your  knowledge and creativity to add details that would make the image more vivid and ' \
                         'interesting. This could include specifying the time of day, weather conditions, surrounding ' \
                         'environment, and any additional elements that could enhance the scene. Your goal is to create a ' \
                         'detailed and descriptive prompt that provides DALL-E  with enough information to generate a rich ' \
                         'and visually appealing image. Remember to maintain the original  intent of my request while ' \
                         'enriching the description with your imaginative details. HOW TO START IMAGE GENERATION: to start ' \
                         'image generation return to me prepared prompt in JSON format, all in one line,  using following ' \
                         'syntax: ~###~{"cmd": "image", "params": {"query": "your query here"}}~###~. Use ONLY this syntax ' \
                         'and remember to surround JSON string with ~###~.  DO NOT use any other syntax. Use English in the ' \
                         'generated JSON command, but conduct all the remaining parts of the discussion with me in the ' \
                         'language in which I am speaking to you. The image will be generated on my machine  immediately ' \
                         'after the command is issued, allowing us to discuss the photo once it has been created.  Please ' \
                         'engage with me about the photo itself, not only by giving the generate command. '
                if 'openai_dalle' not in data['plugins']:
                    data['plugins']['openai_dalle'] = {}
                data['plugins']['openai_dalle']['prompt'] = prompt  # fixed prompt

                updated = True

            # < 2.0.88
            if old < parse_version("2.0.88"):
                print("Migrating config from < 2.0.88...")
                prompt = "AUTONOMOUS MODE:\n1. You will now enter self-dialogue mode, where you will be conversing with " \
                         "yourself, not with a human.\n2. When you enter self-dialogue mode, remember that you are engaging " \
                         "in a conversation with yourself. Any user input will be considered a reply featuring your previous response.\n" \
                         "3. The objective of this self-conversation is well-defined—focus on achieving it.\n" \
                         "4. Your new message should be a continuation of the last response you generated, essentially replying" \
                         " to yourself and extending it.\n5. After each response, critically evaluate its effectiveness " \
                         "and alignment with the goal. If necessary, refine your approach.\n6. Incorporate self-critique " \
                         "after every response to capitalize on your strengths and address areas needing improvement.\n7. To " \
                         "advance towards the goal, utilize all the strategic thinking and resources at your disposal.\n" \
                         "8. Ensure that the dialogue remains coherent and logical, with each response serving as a stepping " \
                         "stone towards the ultimate objective.\n9. Treat the entire dialogue as a monologue aimed at devising" \
                         " the best possible solution to the problem.\n10. Conclude the self-dialogue upon realizing the " \
                         "goal or reaching a pivotal conclusion that meets the initial criteria.\n11. You are allowed to use " \
                         "any commands and tools without asking for it.\n12. While using commands, always use the correct " \
                         "syntax and never interrupt the command before generating the full instruction.\n13. ALWAYS break " \
                         "down the main task into manageable logical subtasks, systematically addressing and analyzing each" \
                         " one in sequence.\n14. With each subsequent response, make an effort to enhance your previous " \
                         "reply by enriching it with new ideas and do it automatically without asking for it.\n15. Any input " \
                         "that begins with 'user: ' will come from me, and I will be able to provide you with ANY additional " \
                         "commands or goal updates in this manner. The other inputs, not prefixed with 'user: ' will represent" \
                         " your previous responses.\n16. Start by breaking down the task into as many smaller sub-tasks as " \
                         "possible, then proceed to complete each one in sequence.  Next, break down each sub-task into even " \
                         "smaller tasks, carefully and step by step go through all of them until the required goal is fully " \
                         "and correctly achieved.\n"
                if 'self_loop' not in data['plugins']:
                    data['plugins']['self_loop'] = {}
                data['plugins']['self_loop']['prompt'] = prompt  # fixed prompt
                updated = True

            # < 2.0.91
            if old < parse_version("2.0.91"):
                print("Migrating config from < 2.0.91...")
                self.window.core.updater.patch_css('style.dark.css', True)  # force replace file
                updated = True

            # < 2.0.96
            if old < parse_version("2.0.96"):
                print("Migrating config from < 2.0.96...")
                if 'img_quality' not in data:
                    data['img_quality'] = "standard"
                updated = True

            # < 2.0.98
            if old < parse_version("2.0.98"):
                print("Migrating config from < 2.0.98...")
                data['img_resolution'] = "1792x1024"  # char fix
                self.window.core.updater.patch_css('style.css', True)  # force replace file
                self.window.core.updater.patch_css('style.light.css', True)  # force replace file
                self.window.core.updater.patch_css('style.dark.css', True)  # force replace file
                updated = True

            # < 2.0.99
            if old < parse_version("2.0.99"):
                print("Migrating config from < 2.0.99...")
                if 'layout.splitters' in data:
                    if 'calendar' in data['layout.splitters']:
                        # restore if was hidden at < 2.0.99
                        if len(data['layout.splitters']['calendar']) == 2 \
                                and data['layout.splitters']['calendar'][1] == 0:
                            data['layout.splitters']['calendar'] = [100, 100]
                if data['layout.density'] == 0:
                    data['layout.density'] = -1
                updated = True

            # < 2.0.100
            if old < parse_version("2.0.100"):
                print("Migrating config from < 2.0.100...")
                # rename output dir to data dir
                src = os.path.join(self.window.core.config.path, 'output')
                dst = os.path.join(self.window.core.config.path, 'data')

                # migrate data dir name
                if os.path.exists(src):
                    # backup old data dir
                    if os.path.exists(dst):
                        backup = os.path.join(self.window.core.config.path, 'data.backup')
                        os.rename(dst, backup)
                    # rename "output" to "data"
                    if os.path.exists(src):
                        os.rename(src, dst)

                # add llama-index config keys:
                if "llama.idx.auto" not in data:
                    data["llama.idx.auto"] = False
                if "llama.idx.auto.index" not in data:
                    data["llama.idx.auto.index"] = "base"
                if "llama.idx.current" not in data:
                    data["llama.idx.current"] = "base"
                if "llama.idx.db.index" not in data:
                    data["llama.idx.db.index"] = ""
                if "llama.idx.db.last" not in data:
                    data["llama.idx.db.last"] = 0
                if "llama.idx.list" not in data:
                    data["llama.idx.list"] = [
                        {
                            "id": "base",
                            "name": "Base",
                        }
                    ]
                if "llama.idx.status" not in data:
                    data["llama.idx.status"] = {}

                if "llama.log" not in data:
                    data["llama.log"] = False

                updated = True

            # < 2.0.101
            if old < parse_version("2.0.101"):
                print("Migrating config from < 2.0.101...")
                if 'layout.tooltips' not in data:
                    data['layout.tooltips'] = True
                updated = True

            # < 2.0.102
            if old < parse_version("2.0.102"):
                print("Migrating config from < 2.0.102...")
                if 'llama.hub.loaders' not in data:
                    data['llama.hub.loaders'] = [
                        {
                            "ext": "pptx",
                            "loader": "PptxReader"
                        },
                        {
                            "ext": "png,jpg,jpeg",
                            "loader": "ImageReader"
                        }
                    ]
                updated = True

            # < 2.0.112
            if old < parse_version("2.0.112"):
                print("Migrating config from < 2.0.112...")
                if 'img_dialog_open' not in data:
                    data['img_dialog_open'] = True
                updated = True

            # < 2.0.114
            if old < parse_version("2.0.114"):
                print("Migrating config from < 2.0.114...")
                if 'llama.idx.storage' not in data:
                    data['llama.idx.storage'] = "SimpleVectorStore"
                if 'llama.idx.storage.args' not in data:
                    data['llama.idx.storage.args'] = []
                if 'llama.idx.raw' not in data:
                    data['llama.idx.raw'] = False
                updated = True

            # < 2.0.116
            if old < parse_version("2.0.116"):
                print("Migrating config from < 2.0.116...")
                data['debug'] = False
                updated = True

            # < 2.0.118
            if old < parse_version("2.0.118"):
                print("Migrating config from < 2.0.118...")
                if 'layout.tray' not in data:
                    data['layout.tray'] = True
                updated = True

            """
            # < 2.0.119
            if old < parse_version("2.0.119"):
                print("Migrating config from < 2.0.119...")
                if 'layout.minimized' not in data:
                    data['layout.minimized'] = False
                updated = True
            """

            # < 2.0.121
            if old < parse_version("2.0.121"):
                print("Migrating config from < 2.0.121...")
                if 'openai_vision' not in data['plugins']:
                    data['plugins']['openai_vision'] = {}
                data['plugins']['openai_vision']['model'] = "gpt-4-vision-preview"
                updated = True

            # < 2.0.123
            if old < parse_version("2.0.123"):
                print("Migrating config from < 2.0.123...")
                if 'llama.idx.recursive' not in data:
                    data['llama.idx.recursive'] = False
                updated = True

            # < 2.0.127
            if old < parse_version("2.0.127"):
                print("Migrating config from < 2.0.127...")
                if 'upload.store' not in data:
                    data['upload.store'] = True
                if 'upload.data_dir' not in data:
                    data['upload.data_dir'] = False
                updated = True

            # < 2.0.131
            if old < parse_version("2.0.131"):
                print("Migrating config from < 2.0.131...")
                if 'self_loop' in data['plugins'] \
                        and 'prompts' not in data['plugins']['self_loop'] \
                        and 'prompt' in data['plugins']['self_loop'] \
                        and 'extended_prompt' in data['plugins']['self_loop']:

                    # copy old prompts to new list of prompts
                    data['plugins']['self_loop']['prompts'] = [
                        {
                            "enabled": True,
                            "name": "Default",
                            "prompt": data['plugins']['self_loop']['prompt'],
                        },
                        {
                            "enabled": False,
                            "name": "Extended",
                            "prompt": data['plugins']['self_loop']['extended_prompt'],
                        },
                    ]
                    updated = True

            # < 2.0.132
            if old < parse_version("2.0.132"):
                print("Migrating config from < 2.0.132...")
                if 'agent.auto_stop' not in data:
                    data['agent.auto_stop'] = True
                if 'agent.iterations' not in data:
                    data['agent.iterations'] = 3
                updated = True

            # < 2.0.135
            if old < parse_version("2.0.135"):
                print("Migrating config from < 2.0.135...")
                if 'agent.mode' not in data:
                    data['agent.mode'] = "chat"
                if 'agent.idx' not in data:
                    data['agent.idx'] = "base"
                updated = True

            # < 2.0.138
            if old < parse_version("2.0.138"):
                print("Migrating config from < 2.0.138...")
                if 'layout.tray.minimize' not in data:
                    data['layout.tray.minimize'] = False
                updated = True

            # < 2.0.139
            if old < parse_version("2.0.139"):
                print("Migrating config from < 2.0.139...")
                data['updater.check.bg'] = True
                if 'license.accepted' not in data:
                    data['license.accepted'] = False
                if 'updater.check.bg.last_time' not in data:
                    data['updater.check.bg.last_time'] = None
                if 'updater.check.bg.last_version' not in data:
                    data['updater.check.bg.last_version'] = None
                updated = True

            # < 2.0.142
            if old < parse_version("2.0.142"):
                print("Migrating config from < 2.0.142...")
                if 'agent.goal.notify' not in data:
                    data['agent.goal.notify'] = True
                updated = True

            # < 2.0.143
            if old < parse_version("2.0.143"):
                print("Migrating config from < 2.0.143...")
                if 'ctx.records.filter' not in data:
                    data['ctx.records.filter'] = "all"
                updated = True

            # < 2.0.144
            if old < parse_version("2.0.144"):
                print("Migrating config from < 2.0.144...")
                if 'cmd_history' in data['plugins'] \
                        and 'syntax_get_ctx_list_in_date_range' in data['plugins']['cmd_history']:
                    # remove
                    del data['plugins']['cmd_history']['syntax_get_ctx_list_in_date_range']
                if 'cmd_history' in data['plugins'] \
                        and 'syntax_get_ctx_content_by_id' in data['plugins']['cmd_history']:
                    # remove
                    del data['plugins']['cmd_history']['syntax_get_ctx_content_by_id']
                updated = True

            # < 2.0.149
            if old < parse_version("2.0.149"):
                print("Migrating config from < 2.0.149...")
                # logger
                if 'log.dalle' not in data:
                    data['log.dalle'] = False
                if 'log.level' not in data:
                    data['log.level'] = "error"
                if 'log.plugins' not in data:
                    data['log.plugins'] = False
                if 'log.assistants' not in data:
                    data['log.assistants'] = False
                if 'log.llama' not in data:
                    if 'llama.log' in data:
                        data['log.llama'] = data['llama.log']
                        del data['llama.log']
                    else:
                        data['log.llama'] = False

                # painter
                if 'painter.brush.color' not in data:
                    data['painter.brush.color'] = 'Black'
                if 'painter.brush.mode' not in data:
                    data['painter.brush.mode'] = 'brush'
                if 'painter.brush.size' not in data:
                    data['painter.brush.size'] = 3
                updated = True

            # < 2.0.152
            if old < parse_version("2.0.152"):
                print("Migrating config from < 2.0.152...")
                data['cmd.prompt'] = self.window.core.config.get_base('cmd.prompt')  # bg run fix
                updated = True

            # < 2.0.153
            if old < parse_version("2.0.153"):
                print("Migrating config from < 2.0.153...")
                if 'layout.dialog.geometry.store' not in data:
                    data['layout.dialog.geometry.store'] = True
                updated = True

            # < 2.0.157
            if old < parse_version("2.0.157"):
                # decrease chunk size
                print("Migrating config from < 2.0.157...")
                if 'cmd_web_google' in data['plugins'] \
                        and 'chunk_size' in data['plugins']['cmd_web_google']:
                    if data['plugins']['cmd_web_google']['chunk_size'] > 20000:
                        data['plugins']['cmd_web_google']['chunk_size'] = 20000
                updated = True

            # < 2.0.161
            if old < parse_version("2.0.161"):
                print("Migrating config from < 2.0.161...")
                if 'ctx.search_content' not in data:
                    data['ctx.search_content'] = False
                if 'download.dir' not in data:
                    data['download.dir'] = "download"
                updated = True

            # < 2.0.162 - migrate indexes into db
            if old < parse_version("2.0.162"):
                print("Migrating indexes from < 2.0.162...")
                if 'llama.idx.replace_old' not in data:
                    data['llama.idx.replace_old'] = True
                self.window.core.idx.patch(old)
                updated = True

            # < 2.0.164 - migrate indexes into db
            if old < parse_version("2.0.164"):
                print("Migrating config from < 2.0.164...")

                # Migrate plugins to provider-based versions

                # rename cmd_web_google to cmd_web
                if 'cmd_web_google' in data["plugins"]:
                    data["plugins"]["cmd_web"] = data["plugins"]["cmd_web_google"]
                    del data["plugins"]["cmd_web_google"]
                if 'cmd_web_google' in data["plugins_enabled"]:
                    data["plugins_enabled"]["cmd_web"] = data["plugins_enabled"]["cmd_web_google"]
                    del data["plugins_enabled"]["cmd_web_google"]

                # rename audio_openai_whisper to audio_input
                if 'audio_openai_whisper' in data["plugins"]:
                    data["plugins"]["audio_input"] = data["plugins"]["audio_openai_whisper"]
                    del data["plugins"]["audio_openai_whisper"]
                if 'audio_openai_whisper' in data["plugins_enabled"]:
                    data["plugins_enabled"]["audio_input"] = data["plugins_enabled"]["audio_openai_whisper"]
                    del data["plugins_enabled"]["audio_openai_whisper"]

                # migrate model to whisper_model
                if 'audio_input' in data["plugins"] and "model" in data["plugins"]["audio_input"]:
                    data["plugins"]["audio_input"]["whisper_model"] = data["plugins"]["audio_input"]["model"]
                    del data["plugins"]["audio_input"]["model"]

                # rename audio_openai_tts to audio_output
                if 'audio_openai_tts' in data["plugins"]:
                    data["plugins"]["audio_output"] = data["plugins"]["audio_openai_tts"]
                    del data["plugins"]["audio_openai_tts"]
                if 'audio_openai_tts' in data["plugins_enabled"]:
                    data["plugins_enabled"]["audio_output"] = data["plugins_enabled"]["audio_openai_tts"]
                    del data["plugins_enabled"]["audio_openai_tts"]

                # migrate model and voice to openai_model and openai_voice
                if 'audio_output' in data["plugins"] and "model" in data["plugins"]["audio_output"]:
                    data["plugins"]["audio_output"]["openai_model"] = data["plugins"]["audio_output"]["model"]
                    del data["plugins"]["audio_output"]["model"]
                if 'audio_output' in data["plugins"] and "voice" in data["plugins"]["audio_output"]:
                    data["plugins"]["audio_output"]["openai_voice"] = data["plugins"]["audio_output"]["voice"]
                    del data["plugins"]["audio_output"]["voice"]

                # migrate azure settings
                if 'audio_azure' in data["plugins"] and "azure_api_key" in data["plugins"]["audio_azure"]:
                    data["plugins"]["audio_output"]["azure_api_key"] = data["plugins"]["audio_azure"]["azure_api_key"]
                if 'audio_azure' in data["plugins"] and "azure_region" in data["plugins"]["audio_azure"]:
                    data["plugins"]["audio_output"]["azure_region"] = data["plugins"]["audio_azure"]["azure_region"]
                if 'audio_azure' in data["plugins"] and "voice_en" in data["plugins"]["audio_azure"]:
                    data["plugins"]["audio_output"]["azure_voice_en"] = data["plugins"]["audio_azure"]["voice_en"]
                if 'audio_azure' in data["plugins"] and "voice_pl" in data["plugins"]["audio_azure"]:
                    data["plugins"]["audio_output"]["azure_voice_pl"] = data["plugins"]["audio_azure"]["voice_pl"]

                # remove audio voice
                if 'audio_output' in data["plugins"] and "voice_en" in data["plugins"]["audio_output"]:
                    del data["plugins"]["audio_output"]["voice_en"]
                if 'audio_output' in data["plugins"] and "voice_pl" in data["plugins"]["audio_output"]:
                    del data["plugins"]["audio_output"]["voice_pl"]

                # remove audio_azure
                if 'audio_azure' in data["plugins"]:
                    del data["plugins"]["audio_azure"]
                if 'audio_azure' in data["plugins_enabled"]:
                    del data["plugins_enabled"]["audio_azure"]

                updated = True

            # < 2.0.165
            if old < parse_version("2.0.165"):
                print("Migrating config from < 2.0.165...")
                if 'llama.idx.excluded_ext' not in data:
                    data['llama.idx.excluded_ext'] = "3g2,3gp,7z,a,aac,aiff,alac,apk,apk,apng,app,ar,avi,avif," \
                                                     "bin,bmp,bz2,cab,class,deb,deb,dll,dmg,dmg,drv,dsd,dylib," \
                                                     "dylib,ear,egg,elf,esd,exe,flac,flv,gif,gz,heic,heif,ico," \
                                                     "img,iso,jar,jpeg,jpg,ko,lib,lz,lz4,m2v,m4a,m4v,mkv,mov,mp3," \
                                                     "mp4,mpc,msi,nrg,o,ogg,ogv,pcm,pkg,pkg,png,psd,pyc,rar,rpm,rpm," \
                                                     "so,so,svg,swm,sys,tar,tiff,vdi,vhd,vhdx,vmdk,vob,war,wav," \
                                                     "webm,webp,whl,wim,wma,wmv,xz,zip,zst"
                if 'cmd_custom' in data["plugins"]:
                    if 'cmds' in data["plugins"]["cmd_custom"]:
                        for i, cmd in enumerate(data["plugins"]["cmd_custom"]["cmds"]):
                            if "enabled" not in cmd:
                                data["plugins"]["cmd_custom"]["cmds"][i]["enabled"] = True
                updated = True

        # update file
        migrated = False
        if updated:
            data = dict(sorted(data.items()))
            self.window.core.config.data = data
            self.window.core.config.save()
            migrated = True

        # check for any missing config keys if versions mismatch
        if is_old:
            if self.window.core.updater.post_check_config():
                migrated = True

        return migrated
