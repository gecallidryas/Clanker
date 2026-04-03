// locales/en.ts (or your desired file name)

// Export the entire locale structure as a default object
export default {
  general: {
    // Common strings
    yes: `Yes`,
    no: `No`,
    confirm: `Confirm`,
    cancel: `Cancel`,
    none: `None`,
    unknown: `Unknown`,

    // Default configuration values
    defaults: {
      bot_name: `Tomori`,
      base_trigger_words: ["tomori", "tomo"],
    },

    // Cooldown messages (slash commands)
    cooldown_title: `⌛ Please wait!`,
    cooldown: `You need to wait {seconds} seconds before using a \`/{category}\` command again.`,

    // Message trigger cooldown messages
    message_cooldown_title: `⌛ Please wait!`,
    message_cooldown: `This server's managers have configured a cooldown. Please wait **{seconds}** seconds before triggering **{botName}** again.`,
    message_cooldown_footer_per_user: `Server Setting: Per-User Cooldown`,
    message_cooldown_footer_per_channel: `Server Setting: Per-Channel Cooldown`,
    message_cooldown_footer_server_wide: `Server Setting: Server-Wide Cooldown`,
    message_cooldown_footer_strict: `Server Setting: Strict Server-Wide Cooldown`,

    // Standard interaction responses (buttons, selects)
    interaction: {
      cancel_title: `🔴 Command Cancelled`,
      cancel_description: `The command has been cancelled.`,
      timeout_title: `⏰ Command Timed Out`,
      timeout_description: `You didn't respond in time. Please try again.`,
    },

    // Pagination component messages
    pagination: {
      page_info: `Page {current} of {total}`,
      previous: `Previous`,
      next: `Next`,
      cancel: `Cancel`,
      no_items: `There are no items to display.`,
      cancelled: `Selection has been cancelled.`,
      timeout: `You didn't make a selection in time. Please try again.`,
      item_selected: `Selected: {item}`,
      select_page_title: `Select Page`,
      select_page_description: `Choose a page to view from {totalItems} items across {totalPages} pages:`,
      select_persona_title: `Select Persona`,
      select_persona_description: `Choose which persona to target first:\n\n{items}`,
      select_persona_description_v2: `Choose which persona to target first.`,
      persona_main_badge: `Main`,
      persona_alter_badge: `Alter`,
      persona_no_attributes: `No attributes configured yet.`,
      persona_select_button: `Select`,
    },

    // Common error messages
    errors: {
      guild_only_title: `Server Only Command`,
      guild_only_description: `This command can only be used within a server.`,
      channel_only_title: `Channel Required`,
      channel_only_description: `This command requires a channel to function properly.`,
      guild_only_command_title: `Server Only Command`,
      guild_only_command_description: `This command can only be used within a server, not in Direct Messages.`,
      channel_not_supported_title: `Unsupported Channel Type`,
      channel_not_supported_description: `Sorry, I can only work in server text channels or Direct Messages. Group DMs and other channel types are not supported.`,
      tomori_not_setup_title: `Initial Setup Required`,
      tomori_not_setup_description: `It seems I haven't been set up on this server yet. A server member with \`Manage Server\` permissions needs to use \`/config setup\` first. You may also use the \`/help setup\` for help, and the \`/config language\` command to set your preferred language.`,
      tomori_updating_title: `Currently Updating...`,
      tomori_updating_description: `I'm currently being updated and will be back shortly. Please try again in a few moments!`,
      tomori_not_setup_dm_footer: `DMs are treated as mini "servers" wherein I respond to any of your messages privately. Most server related commands will still work as intended.`,
      api_key_missing_title: `API Key Missing`,
      api_key_missing_description: `I need an API key to function, but one hasn't been configured for this server. A server member with \`Manage Server\` permissions can set one using \`/config apikey set\`.`,
      api_key_error_title: `API Key Error`,
      api_key_error_description: `There was an issue accessing or decrypting the configured API key. Please ensure it was set correctly using \`/config apikey set\`.`,
      context_error_title: `Context Building Error`,
      context_error_description: `I encountered an error while trying to understand the conversation context.`,
      critical_error_title: `Critical Error`,
      critical_error_description: `An unexpected critical error occurred.`,
      update_failed_title: `Update Failed`,
      update_failed_description: `Failed to update the configuration in the database. Please try again.`,
      unknown_error_title: `Unknown Error`,
      unknown_error_description: `An unexpected error occurred. If the issue persists, please report it through \`/support discord\`.`,
      unexpected_title: `Unexpected Error`,
      unexpected_description: `An unexpected error occurred: {error}`,
      invalid_option_title: `Invalid Option`,
      invalid_option_description: `The selected option is invalid. Please choose a valid option.`,
      permission_denied_title: `Permission Denied`,
      permission_denied_description: `You don't have permission to use this command. Only members with \`Manage Server\` permissions can use this command.`,
      server_not_found_title: `Server Not Found`,
      server_not_found_description: `Server information could not be found in the database. Please try again or contact support if the issue persists.`,
      generic_error_title: `Error`,
      generic_error_description: `An error occurred while processing your request. Please try again later.`,
      brave_api: {
        missing_key: {
          title: `Brave API Key Missing`,
          description: `I need a Brave Search API key to perform searches, but one hasn't been configured for this server. A server member with \`Manage Server\` permissions can set one using \`/optionalkey brave set\`.`,
          footer: `Learn how using /help apikey`,
        },
      },
      duckduckgo_rate_limit: {
        title: `DuckDuckGo Rate Limited`,
        description: `DuckDuckGo search is currently rate limited. For more reliable searching, a server member with \`Manage Server\` permissions can set up Brave Search using \`/optionalkey brave set\`.`,
        footer: `Learn how using /help apikey`,
      },
      operation_failed_title: `Operation Failed`,
      operation_failed_description: `The requested operation could not be completed. Please try again.`,
      provider_not_supported_title: `Provider Not Supported`,
      provider_not_supported_description: `The selected AI provider is not currently supported.`,
      user_blacklisted_title: `User Blacklisted`,
      user_blacklisted_description: `You are currently blacklisted from personalization features on this server and cannot perform this action.`,
      persona_response_failed_title: `Persona Response Failed`,
      persona_response_failed_description: `Failed to generate a response from persona **{personaName}**. Please try again.`,
      webhook_missing_permissions_title: `Missing Webhook Permissions`,
      webhook_missing_permissions_description: `I can't create webhooks in this channel, so alter personas will use regular bot messages. Please grant me the **Manage Webhooks** permission in this channel to enable custom alter avatars.`,
      webhook_limit_title: `Webhook Limit Reached`,
      webhook_limit_description: `This channel has reached Discord's webhook limit (10), so alter personas will use regular bot messages. Please delete unused webhooks or reduce the number of alters responding in this channel.`,
      webhook_unknown_error_title: `Webhook Error`,
      webhook_unknown_error_description: `I couldn't create a webhook in this channel, so alter personas will use regular bot messages. Please check my permissions and try again.`,
      voice_transcription_unavailable_title: `Voice Transcription Unavailable`,
      voice_transcription_unavailable_description: `Voice transcription isn't available here yet. Configure an ElevenLabs key with \`/optionalkey elevenlabs set\` and try again.`,
      voice_transcription_failed_title: `Voice Transcription Failed`,
      voice_transcription_failed_description: `I couldn't transcribe that audio message. Please try again or send the message as text instead.`,
    },
    tomori_busy_title: "Busy Replying to Someone Else!",
    tomori_busy_replying:
      "Currently responding to this message: {message_link}. Your message has been queued.",
  },

  rate_limit: {
    // User-level rate limiting (DM notification)
    user_exceeded_title: `🟡️ Rate Limit Reached`,
    user_exceeded_description: `You currently have too much active messages being processed across all servers. To prevent abuse, your most recent trigger attempt has been dropped. Please wait for some of your messages to finish processing before sending more.`,

    // Server-level rate limiting (public channel notification)
    server_exceeded_title: `🟡️ Server Overloaded`,
    server_exceeded_description: `This server currently has too much active messages being processed. I'm at capacity right now! Please try again in a moment, or use me in another server or via Direct Messages instead.`,

    error_memory_critical_title: `🔴 System Overloaded`,
    error_memory_critical_description: `I'm currently experiencing high memory usage, preventing file uploads. Please try again in a moment.`,

    error_quota_exceeded_title: `🔴 Daily Limit Reached`,
    error_quota_exceeded_description: `You've reached the daily limit for this command. Your quota resets at **{reset_time}**. Please try again after the reset time.`,
  },

  genai: {
    // Errors related to LLM API generation
    generic_error_title: `Generation Error`,
    generic_error_description: `{error_message}`,
    generic_error_footer: `Please run \`/tool refresh\` and then try again. If the issue persists, please report it through \`/support discord\`.`,
    error_stream_timeout_title: "Connection Timeout",

    // Provider error format template: "{Provider name} Error Code {number}: {message from Google}. {tip from us}"
    provider_error_format:
      "{providerName} Error Code {errorCode}: {apiMessage}. {tip}",
    error_stream_timeout_description:
      "If this keeps happening, there might be a temporary issue with your chosen AI provider. Please try again later or use `/tool refresh` to refresh the context history.",

    // Empty response from API
    empty_response_title: `Empty Response`,
    empty_response_description: `I received an empty response from the AI, use \`/tool refresh\` if this issue persists.`,
    // New: Max iterations for function calls
    max_iterations_title: "Thinking Loop",
    max_iterations_streaming_description:
      "I got stuck in a thinking loop and couldn't complete the request, use `/tool refresh` if this issue persists.",

    // NAI tool retry exhaustion
    nai_tool_retry_exhausted_title: "Tool Error",
    nai_tool_retry_exhausted_description:
      "A tool failed multiple times and couldn't complete the request. Please try again or use `/tool refresh` if this issue persists.",

    // Fallback model info (shown when primary model fails but a fallback succeeded)
    fallback_used_title: `Fallback Model Used`,
    fallback_used_description: `\`{success_model}\` was used instead of {chain}`,

    // Generic no response warning (for unknown status or unhandled cases)
    no_response_title: `No Response`,
    no_response_description: `I didn't respond - this may be due to an empty response or timeout from the AI.`,
    thought_log: {
      title: `Thought Log`,
      description: `Source: {source_line}`,
      summary_field: `Thought Summary`,
      raw_field: `Raw Thoughts`,
      footer: `Provider: {provider} | Model: {model}`,
    },

    // Text quota errors
    text_quota_exceeded_title: `🔴 Text Quota Exceeded`,
    text_quota_exceeded_description: `You have reached your text generation quota. {reset_info}`,
    text_user_quota_exceeded_description: `You have reached your daily text generation quota. {reset_info}`,
    text_serverwide_quota_exceeded_description: `This server has reached its text generation quota for this period. {reset_info}`,
    text_quota_resets_in_hours: `Quota resets in {hours} hour(s).`,
    text_quota_resets_in_days: `Quota resets in {days} day(s).`,
    text_quota_exceeded_footer: `This quota is configured by this server's managers via \`/server quota\`.`,

    // Search related messages
    search: {
      web_search_title: `🔍 Searching for \`{query}\` on the web...`,
      image_search_title: `🔍 Searching for \`{query}\` images...`,
      video_search_title: `🔍 Searching for \`{query}\` videos...`,
      news_search_title: `🔍 Searching for \`{query}\` in the news...`,
      disclaimer_description: `AI-Generated Responses and Search Results may be inaccurate or incomplete, **please double-check important information**.`,
    },

    // Custom MCP server tool usage messages
    mcp: {
      tool_invoke_title: `🔧 Using \`{function}\` from **{server}**...`,
      tool_invoke_description: `Parameters:`,
      tool_invoke_no_params: `No parameters.`,
    },

    // YouTube video processing messages
    video: {
      youtube_processing_title: "👁️  Watching YouTube Video...",
      youtube_processing_description:
        "I'm currently watching the YouTube video: {video_url}",
      youtube_processing_footer:
        "This may take a moment depending on the video length",
    },

    // Inline document reading messages (read_document tool)
    document: {
      reading_title: "📄 Reading Document...",
      reading_description: "Reading the contents of `{filename}`",
    },

    image: {
      generating_title: "🖼️  Generating Image...",
      generating_description: "Creating an image from the current prompt",
      generating_with_references_description:
        "Creating an image from the current prompt and reference image(s)",
      editing_title: "🖌️  Editing Image...",
      editing_description:
        "Editing the referenced image by targeting `{edit_target}`",
      generating_footer: "This may take a moment depending on provider load",
    },

    vision: {
      analyzing_title: "🖼️  Analyzing Image...",
      analyzing_description:
        "Current model is non-vision; using configured vision model to analyze images",
      analyzing_footer: "This may take a moment depending on image count",
    },

    gif: {
      processing_title: "🎞️  Processing GIF...",
      processing_description:
        "Extracting keyframes from the requested GIF for closer analysis",
      processing_footer: "Large GIFs can take a bit longer",
    },

    fetch: {
      reading_title: "🌐  Reading Webpage...",
      reading_description: "Fetching and reading: {url}",
      reading_footer: "This may take a moment depending on the page size",
    },

    // New: Stream specific error messages
    stream: {
      response_stopped_title: "Response Interrupted",
      response_stopped_description:
        "The response was interrupted for the following reason: {reason}. Make sure that content sent is not too large for the AI provider to handle. Run `/tool refresh` to clear conversation content.",
      prohibited_content_title: "Content Policy Violation",
      prohibited_content_description:
        "The response was blocked due to prohibited content detection.",
      prohibited_content_admin_notice_title: "Admin Notice",
      prohibited_content_admin_notice_description:
        "Check: messages (`/tool refresh`), personality/memories (`/data export`), blacklist problematic members (`/server blacklist`), or switch provider (`/config model`)",
      streaming_failed_description:
        "An issue while trying to stream the response.",

      // Error interaction messages
      provider_error_interaction:
        "Stream response blocked/stopped. Reason: {reason}.",
      retry_message: "This error is temporary. You can try again later.",

      // Universal provider error titles and tips (moved from genai.google)
      api_error_title: "🔴 Provider API Error",
      api_error_tip:
        "Please verify your API key and try again. If this error persists, report through `/support discord`",

      rate_limit_title: "🟡 Provider Rate Limit Exceeded",
      rate_limit_title_all_rotation_keys:
        "🟡 Provider Rate Limit Exceeded (All Rotation Keys)",
      rate_limit_tip:
        "Please wait a few minutes before trying again. If you have multiple personal keys, consider `/config apikey rotation`.",
      model_fallback_hint:
        "For better resilience, you can configure model failover with `/config model fallback`.",

      content_blocked_title: "🔴️ Provider Content Filter",
      content_blocked_tip:
        "Tip: You can turn on `/config uncensors` options to help prevent this error. You may also check messages (`/tool refresh`), personality/memories (`/data export`), blacklist problematic members (`/server blacklist`), or switch provider (`/config model`)",

      timeout_title: "🟡️ Provider Request Timeout",
      timeout_tip: "Try shortening your message or try again",

      provider_overloaded_title: "🔴 Provider Overloaded",
      provider_overloaded_tip:
        "Provider is currently experiencing unexpectedly high usage, please try again later or swap to a different provider",

      unknown_title: "🔴 Provider Error",
      unknown_tip:
        "Please try again or use `/support discord` if this keeps happening",

      flush_limit_title: "🟡️ Response Length Limit Reached",
      flush_limit_description:
        "This response has reached the maximum message length limit and has been stopped. You can use `/bot respond` to manually continue the response if needed.",

      inactivity_timeout_title: "🟡️ Response Timed Out",
      inactivity_timeout_description:
        "The AI provider stopped responding and the connection timed out. This can happen when the provider is overloaded or experiencing issues. Please try again.",
    },

    // Google-specific error messages (provider-specific default messages only)
    google: {
      // 400 INVALID_ARGUMENT
      "400_default_message": "There was an error in your request format",

      // 400 FAILED_PRECONDITION (billing)
      "400_billing_default_message": "Billing is required for this service",

      // 403 PERMISSION_DENIED
      "403_default_message":
        "Your API key doesn't have the required permissions. Please ensure you're using your own legally obtained API key from Google AI Studio",

      // 404 NOT_FOUND
      "404_default_message": "A referenced resource could not be found",

      // 429 RESOURCE_EXHAUSTED
      "429_default_message": "You've sent too many requests too quickly",

      // 500 INTERNAL
      "500_default_message": "An unexpected error occurred on Google's servers",

      // 503 UNAVAILABLE
      "503_default_message": "The AI model is currently overloaded",

      // 504 DEADLINE_EXCEEDED
      "504_default_message": "Your request took too long to process",

      // Content blocked errors (SAFETY, PROHIBITED_CONTENT, etc.)
      content_blocked_default_message:
        "Your content was blocked by safety filters",

      // Generic fallback for unknown Google errors
      unknown_default_message: "An unexpected error occurred",
    },

    // NovelAI-specific error messages (provider-specific default messages only)
    novelai: {
      // 400 BAD_REQUEST
      "400_default_message": "Invalid request format or parameters",

      // 400 BAD_REQUEST - Trial account recaptcha requirement
      "400_trial_message":
        "Your trial account requires recaptcha verification for generations. API access requires a paid NovelAI subscription. Please upgrade your account at https://novelai.net/",

      // 401 UNAUTHORIZED
      "401_default_message": "Your NovelAI API key is invalid or expired",

      // 402 PAYMENT_REQUIRED
      "402_default_message": "You don't have enough Anlas credits",

      // 429 TOO_MANY_REQUESTS
      "429_default_message":
        "You're sending too many requests, please slow down",

      // 503 SERVICE_UNAVAILABLE
      "503_default_message": "NovelAI servers are currently overloaded",

      // 504 GATEWAY_TIMEOUT
      "504_default_message": "Your request took too long to process",

      // Generic fallback for unknown NovelAI errors
      unknown_default_message: "An unexpected error occurred",
    },

    // OpenRouter-specific error messages (provider-specific default messages only)
    openrouter: {
      // 400 BAD_REQUEST
      "400_default_message":
        "Bad request: invalid or missing params, or CORS issue",

      // 401 UNAUTHORIZED
      "401_default_message":
        "Invalid credentials: OAuth session expired or disabled/invalid API key",

      // 402 PAYMENT_REQUIRED
      "402_default_message":
        "Your account or API key has insufficient credits. Add more credits and retry the request.",

      // 403 FORBIDDEN
      "403_default_message":
        "Your chosen model requires moderation and your input was flagged",

      // 404 NOT_FOUND
      "404_default_message":
        "No endpoints found that support the requested features (tools/images). Try a different model using the `/config model text` command.",

      // 404 Privacy Policy Error
      "404_privacy_policy_error":
        "**Privacy Policy Restriction**\n" +
        "The selected model requires allowing data for paid model training, but your OpenRouter account privacy settings currently block this.\n\n" +
        "**To fix this:**\n" +
        "1. Visit https://openrouter.ai/settings/privacy\n" +
        '2. Adjust your "Data Policy" settings to allow this model\n' +
        "3. Or select a different model that matches your privacy preferences",

      // 408 REQUEST_TIMEOUT
      "408_default_message": "Your request timed out",

      // 413 PAYLOAD_TOO_LARGE
      "413_default_message":
        "Request body too large (context/media exceeds provider limits). Try using `/tool refresh` to clear conversation history, or reduce the amount of media/memories in context.",

      // 429 TOO_MANY_REQUESTS
      "429_default_message":
        "You are being rate limited. Please retry shortly, or use a different model that isn't free.",

      // 502 BAD_GATEWAY
      "502_default_message":
        "Your chosen model is down or we received an invalid response from it",

      // 503 SERVICE_UNAVAILABLE
      "503_default_message":
        "There is no available model provider that meets your routing requirements",

      // invalid_type error (parameter type mismatch)
      invalid_type_default_message:
        "Request contains a parameter with an invalid type. This may be a compatibility issue with the selected model. Try using `/tool refresh` to clear context, or try a different model.",

      // Generic fallback for unknown OpenRouter errors
      unknown_default_message: "An unexpected error occurred",
    },

    deepseek: {
      connection_refused:
        "Could not connect to the DeepSeek API endpoint. Please try again later.",

      "401_default_message":
        "Your DeepSeek API key is invalid or does not have access to this model.",

      "402_default_message":
        "Your DeepSeek account does not have sufficient credits for this request.",

      "403_default_message":
        "DeepSeek denied this request. Please verify your account and model access.",

      "404_default_message":
        "The requested DeepSeek model or API route could not be found.",

      "408_default_message":
        "The DeepSeek request timed out before the provider responded.",

      "429_default_message":
        "DeepSeek is rate limiting this request. Please wait a moment and try again.",

      "429_plan_access_default_message":
        "Your DeepSeek subscription plan does not include access to this model. Please switch to a different model with `/config model text`.",

      "500_default_message": "DeepSeek returned an internal server error.",

      "503_default_message": "DeepSeek is currently unavailable or overloaded.",

      unknown_default_message:
        "An unexpected error occurred while communicating with DeepSeek.",
    },

    nvidia: {
      connection_refused:
        "Could not connect to the NVIDIA API endpoint. Please try again later.",

      "401_default_message":
        "Your NVIDIA API key is invalid or does not have access to this model.",

      "402_default_message":
        "Your NVIDIA account does not have sufficient credits for this request.",

      "403_default_message":
        "NVIDIA denied this request. Please verify your account and model access.",

      "404_default_message":
        "The requested NVIDIA model or API route could not be found.",

      "408_default_message":
        "The NVIDIA request timed out before the provider responded.",

      "429_default_message":
        "NVIDIA is rate limiting this request. Please wait a moment and try again.",

      "500_default_message": "NVIDIA returned an internal server error.",

      "503_default_message": "NVIDIA is currently unavailable or overloaded.",

      unknown_default_message:
        "An unexpected error occurred while communicating with NVIDIA.",
    },

    // Z.ai provider error messages
    zai: {
      connection_refused:
        "Could not connect to the Z.ai API endpoint. Please try again later.",

      "401_default_message":
        "Your Z.ai API key is invalid or does not have access to this model.",

      "402_default_message":
        "Your Z.ai account does not have sufficient credits for this request.",

      "403_default_message":
        "Z.ai denied this request. Please verify your account and model access.",

      "404_default_message":
        "The requested Z.ai model or API route could not be found.",

      "429_default_message":
        "Z.ai is rate limiting this request. Please wait a moment and try again.",

      "429_balance_default_message":
        "Your Z.ai account does not have enough balance or credits for this request.",

      "429_plan_access_default_message":
        "Your Z.ai subscription plan does not include access to this model. Please switch to a different model with `/config model text`.",

      "500_default_message": "Z.ai returned an internal server error.",

      "503_default_message": "Z.ai is currently unavailable or overloaded.",

      unknown_default_message:
        "An unexpected error occurred while communicating with Z.ai.",
    },

    // Custom provider error messages (self-hosted OpenAI-compatible endpoints)
    custom: {
      // Connection errors
      connection_refused:
        "Could not connect to the custom endpoint. Please verify that your local LLM server is running and accessible at the configured URL.",

      // HTTP status errors
      "401_default_message":
        "Authentication failed. If your endpoint requires an API key, please check that it's configured correctly.",

      "403_default_message":
        "Access denied by the custom endpoint. Please check your endpoint's access controls.",

      "404_default_message":
        "Resource not found. For Ollama users: verify your model name is correct (use `/config setup` to update). Otherwise, check that your endpoint URL includes the proper path (e.g., /v1/chat/completions).",

      "408_default_message":
        "Request timed out. The custom endpoint took too long to respond.",

      "429_default_message":
        "Rate limited by the custom endpoint. Please wait a moment and try again.",

      "500_default_message":
        "Internal server error from the custom endpoint. Please check your LLM server logs.",

      "502_default_message":
        "Bad gateway error. The custom endpoint returned an invalid response.",

      "503_default_message":
        "Custom endpoint is currently unavailable. Please ensure your LLM server is running.",

      // Generic fallback
      unknown_default_message:
        "An unexpected error occurred while communicating with the custom endpoint.",
    },

    self_teach: {
      server_memory_learned_title:
        "🧠 {persona_nickname} Learned Something New!",
      server_memory_learned_description:
        "A server memory has been saved:\n`{memory_content}`",
      server_memory_updated_title: "📝 {persona_nickname} Updated a Memory!",
      server_memory_updated_description:
        "A server memory has been updated:\n`{memory_content}`",
      personal_memory_learned_title:
        "💡 {persona_nickname} Learned Something New about {user_nickname}!",
      personal_memory_learned_description:
        "A personal memory about {user_nickname} has been saved:\n`{memory_content}`",
      personal_memory_updated_title:
        "📝 {persona_nickname} Updated Memory about {user_nickname}!",
      personal_memory_updated_description:
        "A personal memory about {user_nickname} has been updated:\n`{memory_content}`",
      server_memory_footer:
        "Server managers can manage this memory using `/teach` and `/forget` commands. Use `/data export` to view the full text.",
      personal_memory_footer_manage:
        "You can manage your personal memories using `/teach` and `/forget` commands. Use `/data export` to view the full text. Opt out of personal memory storage with `/personal privacy`.",
      personal_memory_footer_personalization_disabled:
        "This memory was saved, but personalization features are currently disabled on this server, so it will not have an immediate effect here. Use `/data export` to view the full text. Opt out of personal memory storage with `/personal privacy`.",
      personal_memory_footer_user_blacklisted:
        "This memory was saved, but the user in question is currently blacklisted from personalization features on this server, so it will not have an immediate effect here. Use `/data export` to view the full text. Opt out of personal memory storage with `/personal privacy`.",
    },
  },

  commands: {
    // Reusable choice localizations for common options
    choices: {
      add: "Add",
      remove: "Remove",
      always: "Always",
      enable: "Enable",
      disable: "Disable",
      enabled: "Enabled",
      disabled: "Disabled",
      on: "On",
      off: "Off",
      yes: "Yes",
      no: "No",
      true: "True",
      false: "False",
      opt_out: "Block Memory Storage",
      opt_in: "Allow Memory Storage",
      none: "None",
      inherit_global: "Inherit Global Cooldown",
    },

    // SillyTavern preset management
    stpreset: {
      description: `Manage SillyTavern presets`,
      upload: {
        description: `Upload a SillyTavern preset JSON file`,
        file_description: `The SillyTavern preset .json file to upload`,
        invalid_file_title: `Invalid File`,
        invalid_format: `Only \`.json\` files are accepted. Please upload a SillyTavern preset JSON file.`,
        file_too_large_title: `File Too Large`,
        file_too_large_description: `The preset file must be under {max_size} MB.`,
        download_failed: `Failed to download the attachment. Please try again.`,
        invalid_json: `The file could not be parsed as valid JSON.`,
        not_a_preset: `This doesn't look like a SillyTavern preset — no \`prompts\` array found.`,
        no_nodes: `No usable prompt nodes were found in this preset.`,
        duplicate_name: `A preset named "{name}" already exists for this server. Remove it first or rename the file.`,
        success_title: `Preset Uploaded`,
        success_description: `**{name}** has been imported.\n\n• **{total}** total nodes\n• **{markers}** structural markers\n• **{toggleable}** toggleable nodes (**{enabled}** enabled)\n{notes}\nUse \`/stpreset node toggle\` to adjust which nodes are active.\nUse \`/stpreset remove\` to revert to default behavior.`,
        note_comment_only: `\n> **{count}** comment-only node(s) were skipped (contain only \`{{// comments}}\` and produce no output).`,
        note_disabled_by_preset: `> **{count}** node(s) are disabled by default in this preset. Use \`/stpreset node toggle\` to enable them.\n`,
      },
      remove: {
        description: `Remove the active SillyTavern preset`,
        no_preset_title: `No Active Preset`,
        no_preset_description: `There is no active SillyTavern preset on this server. Nothing to remove.`,
        failed_title: `Removal Failed`,
        failed_description: `Failed to remove the preset. Please try again.`,
        success_title: `Preset Removed`,
        success_description: `**{name}** has been removed. Context assembly has reverted to the default behavior.`,
      },
      node: {
        description: `Manage preset prompt nodes`,
        toggle: {
          description: `Toggle preset prompt nodes on or off`,
          no_preset_title: `No Preset Found`,
          no_preset_description: `No active SillyTavern preset found for this server. Upload one with \`/stpreset upload\` first.`,
          no_nodes_title: `No Toggleable Nodes`,
          no_nodes_description: `This preset has no toggleable prompt nodes.`,
          select_page_title: `Select Page`,
          select_page_description: `**{preset_name}** has **{total_nodes}** toggleable nodes across **{total_pages}** pages.\nSelect a page to view and toggle nodes:`,
          group_description: `Check to enable, uncheck to disable`,
          done_button: `Done`,
          no_changes: `No changes made`,
          result_title: `Node Toggle Results`,
          result_description: `**{enabled}** / **{total}** nodes enabled.\n\n{changes}`,
        },
      },
    },

    // General utility commands
    tool: {
      ping: {
        description: `Check the bot's latency.`,
        title: `Pong! 🏓`,
        response_fast: `Response Time: \`{response_time}ms\``,
        response_slow: `Response Time: \`{response_time}ms\``,
      },
      estimate: {
        description: `Estimate usage and costs`,
        cost: {
          description: `Estimate API costs for paid AI providers`,
          title: `Estimated API Costs`,
          embed_description: `Here are **VERY ROUGH** estimated costs per trigger in a Discord channel when using paid AI providers. Costs are estimated using example **{provider}** costs (Input: {inputPrice}/M tokens, Output: {outputPrice}/M tokens)`,
          current_context_description: `Estimated cost for your **current context only**. Input tokens are measured by the provider API using your current setup and recent channel history on **{provider}** model **{model}**. Output tokens remain estimated. Pricing used: Input {inputPrice}/M, Output {outputPrice}/M.`,
          current_input_title: `Measured Input Tokens (Current Context)`,
          current_input_value: `**Input:** {inputTokens} tokens\n**Input cost only:** ~{inputCost} per trigger`,
          current_output_short_title: `Estimated Output: Short`,
          current_output_typical_title: `Estimated Output: Typical`,
          current_output_long_title: `Estimated Output: Long`,
          current_output_band_value: `**Output estimate:** {outputTokens} tokens\n**Total estimate:** {totalTokens} tokens\n**Cost:** ~{costPerMessage} per trigger (~{costPer100} per 100 triggers)`,
          current_footer: `Input token counts are provider-measured only for providers with live counting support. Output token counts are estimated only.`,
          no_cost_provider_description: `Current provider does not have costs`,
          unavailable_description: `Live cost estimation is not available for the current provider (**{provider}**).`,
          fallback_notice_title: `Live Counting Unavailable`,
          fallback_notice_value: `Live provider token counting could not be used for your current setup, so this view is a rough fallback estimate.`,
          minimum_scenario_title: `Minimum Scenario (Light Usage)`,
          minimum_scenario_value: `**Context:** 1 user with 0 memories, 1 paragraph of persona, conversations are less than a sentence per message
**Tokens:** {inputTokens} input + {outputTokens} output = {totalTokens} total
**Cost:** ~{costPerMessage} per trigger (~{costPer100} per 100 triggers)`,
          average_scenario_title: `Average Scenario (Moderate Usage)`,
          average_scenario_value: `**Context:** 3 users with 10 memories each, ~16 paragraphs of persona (includes attributes & dialogues), conversations are 1-2 sentences per message
**Tokens:** {inputTokens} input + {outputTokens} output = {totalTokens} total
**Cost:** ~{costPerMessage} per trigger (~{costPer100} per 100 triggers)`,
          maximum_scenario_title: `Maximum Scenario (Heavy Usage)`,
          maximum_scenario_value: `**Context:** 5 users with 25 memories each, ~31 paragraphs of persona (includes attributes & dialogues), conversations are 2 paragraphs per message
**Tokens:** {inputTokens} input + {outputTokens} output = {totalTokens} total
**Cost:** ~{costPerMessage} per trigger (~{costPer100} per 100 triggers)`,
          breakdown_title: `What Affects Cost?`,
          breakdown_value: `**Input tokens (context sent to AI):**
- Persona paragraphs (includes attributes & sample dialogues)
- Server & personal memories
- Enabled tools (if any)
- User statuses & reminders
- Recent conversation history (includes images, videos, stickers, emojis, embeds if provider supports)
- Server emojis (10 constant)

**Output tokens (AI response):**
- Response length varies by query complexity
- More detailed questions = longer responses = higher cost

**Tips to reduce costs:**
I have built-in features to help reduce costs from abusers or spammers in your server, but here are some additional tips:
- Use fewer persona paragraphs (attributes & dialogues)
- Keep memories concise
- Use free AI providers (Google Gemini free tier)
- Limit auto-trigger channels`,
          footer: `Free providers like Google Gemini (free tier) and some OpenRouter models have no cost! NovelAI offers unlimited usage with a subscription. Use \`/help apikey\` to learn more.`,
        },
      },
      compact: {
        description: `Summarize the recent conversation into a compact system memory.`,
        channel_description: `Optional channel to post the summary in (defaults to this channel).`,
        modal: {
          title: `Compact Summary`,
          type_label: `Summary Type`,
          type_description: `Choose the summary format to generate.`,
          type_choice_conversation: `Conversation`,
          type_choice_roleplay: `Roleplay`,
          refresh_label: `Refresh Context?`,
          refresh_description: `If Yes, messages above the summary will be ignored.`,
          analyze_images_label: `Analyze Images?`,
          analyze_images_description: `Include image analysis for attachments, emojis, and stickers.`,
          additional_instructions_label: `Additional Instructions`,
          additional_instructions_placeholder: `Optional: add extra guidance for the summary output.`,
        },
        processing_title: `⏳ Building Summary`,
        processing_description: `I'm compacting the recent conversation now...`,
        success_title: `✅ Summary Posted`,
        success_description: `Your compact summary has been posted in this channel.`,
        success_description_redirect: `Your compact summary has been posted in {channel}.`,
        failed_title: `Summary Failed`,
        failed_description: `I couldn't generate the summary: {error}`,
        provider_unsupported_title: `Provider Not Supported`,
        provider_unsupported_description: `The current provider ({provider}) does not support compact summaries. Please switch to a compatible provider.`,
        model_incompatible_title: `Model Incompatible`,
        model_incompatible_description: `The current model ({model_name}) does not support structured output (STRUCT) required for roleplay summaries.`,
        image_vision_required_title: `Image Vision Required`,
        image_vision_required_description: `The current model ({model_name}) cannot analyze images. Please choose a vision-capable model or disable image analysis.`,
        summary_title: `🧠 Compact Summary`,
        summary_title_refreshed: `🧹 Compact Summary (Refreshed)`,
        roleplay_scene_title: `🎭 Roleplay Scene Summary`,
        roleplay_scene_title_refreshed: `🧹 Roleplay Scene Summary (Refreshed)`,
        roleplay_scene_synopsis_header: `Synopsis of the current story:`,
        roleplay_character_title_prefix: `🎭 Character Summary:`,
        roleplay_labels: {
          character: `Character summary for`,
          current_goals: `Immediate Goals of`,
          emotional_status: `Current Emotional Status of`,
          physical_status: `Current Physical Status of`,
          appearance_clothing: `Appearance/Clothing of`,
          inventory: `Inventory of`,
        },
        refresh_footer: `Context refreshed starting with this embed.`,
      },
      refresh: {
        description: `Clears the recent conversation history.`,
        title: `🧹 Conversation History Cleared`,
        response: `Context has been refreshed. All messages above this one will now be ignored.`,
      },
      status: {
        description: `Show current personal, server, or persona status.`,
        scope_description: `Which scope to display status for?`,
        scope_choice_personal: `Personal`,
        scope_choice_server: `Server`,
        scope_choice_persona: `Persona`,
        // Personal scope (1 page)
        personal_title: `Personal Status`,
        personal_description: `Your personal settings and global personal memory`,
        // Server scope (5 pages)
        server_title: `Server Status`,
        server_description: `Server configuration and moderation settings`,
        server_page1_title: `Server Status: Model and Sampling`,
        server_page1_description: `Language model and sampler configuration`,
        server_page2_title: `Server Status: Behavior`,
        server_page2_description: `Timing, limits, and cooldown settings`,
        server_page3_title: `Server Status: Channels and Automation`,
        server_page3_description: `Auto-chat, RP channels, whitelist, and random triggers`,
        server_page4_title: `Server Status: Features and Moderation`,
        server_page4_description: `Feature toggles and moderation settings`,
        server_page5_title: `Server Status: System Prompt`,
        server_page5_description: `Active server system prompt preview`,
        server_page6_title: `Server Status: Model Overrides`,
        server_page6_description: `Channel and persona model overrides`,
        server_page7_title: `Server Status: Quotas`,
        server_page7_description: `Complete image and text quota settings`,
        // Persona scope (persona picker + 5 pages)
        persona_page1_title: `{persona_name}: Identity`,
        persona_page1_description: `Persona identity and trigger words`,
        persona_page2_title: `{persona_name}: Attributes`,
        persona_page2_description: `Persona attributes with truncated preview`,
        persona_page3_title: `{persona_name}: Sample Dialogues`,
        persona_page3_description: `Persona sample dialogue pairs with truncated preview`,
        persona_page4_title: `{persona_name}: Memories`,
        persona_page4_description: `Persona-scoped personal and server memories for you`,
        persona_page5_title: `{persona_name}: Prompt and Tags`,
        persona_page5_description: `Persona prompt and generation tags`,
        // Shared fields
        field_model: `AI Model`,
        field_temperature: `Temperature`,
        field_top_p: `Top-P`,
        field_top_k: `Top-K`,
        field_min_p: `Min-P`,
        field_frequency_penalty: `Frequency Penalty`,
        field_presence_penalty: `Presence Penalty`,
        field_humanizer: `Humanizer Level`,
        field_timezone: `Server Timezone`,
        field_message_fetch_limit: `Message Fetch Limit`,
        field_autoch_threshold: `Auto-Chat Mode`,
        field_autoch_channels: `Auto-Chat Channels`,
        field_rp_channels: `RP Channels`,
        field_thought_logs_channel: `Thought Logs Channel`,
        field_welcome_channel: `Welcome Channel`,
        field_welcome_persona: `Welcome Persona`,
        field_trigger_words: `Trigger Words`,
        field_whitelist_channels: `Channel Whitelist`,
        field_whitelist_roles: `Role Whitelist`,
        whitelist_all_allowed: `None (all channels can trigger)`,
        whitelist_roles_all_allowed: `None (all roles can trigger)`,
        field_random_triggers: `Random Triggers`,
        field_channel_llm_overrides: `Channel Model Overrides`,
        field_persona_llm_overrides: `Persona Model Overrides`,
        random_trigger_persona_random: `Random`,
        field_cooldown_type: `Cooldown Type`,
        field_cooldown_length: `Cooldown Duration`,
        field_cooldown_length_value: `{seconds}s`,
        field_self_reply_limit: `Self-Reply Limit`,
        field_send_message_limit: `Send Limit`,
        field_always_reply: `Always-Reply`,
        field_triggered_persona_limit: `Triggered Persona Limit`,
        field_personalization: `Personal Memories`,
        field_self_teach: `Self-Teaching`,
        field_pin_message: `Pin Message Tool`,
        field_hide_respond_embed: `Hide Respond Embed`,
        field_self_debug: `Self-Debug Error Embeds`,
        field_blacklisted_members: `Blacklisted Members`,
        field_api_key_set: `API Key Set`,
        field_brave_api_key_set: `Brave API Key Set`,
        field_emoji_usage: `Emoji Usage`,
        field_sticker_usage: `Sticker Usage`,
        field_web_search: `Web Search`,
        field_image_generation: `Image Generation`,
        field_videogen: `Video Generation`,
        field_server_memteaching: `Server Memories Teaching`,
        field_attribute_memteaching: `Attributes Teaching`,
        field_sampledialogue_memteaching: `Sample Dialogues Teaching`,
        field_hide_impersonation: `Hide Impersonation Embeds`,
        field_uncensor_injection: `Anti-Injection Prompt`,
        field_uncensor_unicode: `Unicode Space Replacement`,
        field_uncensor_sanitize: `Word Sanitization`,
        field_image_quota_enabled: `Image Quota Enabled`,
        field_image_quota_daily_user: `Image Daily User Quota`,
        field_image_quota_serverwide: `Image Server-wide Quota`,
        field_image_quota_reset_days: `Image Quota Reset Period`,
        field_text_quota_enabled: `Text Quota Enabled`,
        field_text_quota_daily_user: `Text Daily User Quota`,
        field_text_quota_serverwide: `Text Server-wide Quota`,
        field_text_quota_reset_days: `Text Quota Reset Period`,
        field_quota_reset_days_value: `{days} day(s)`,
        field_quota_unlimited: `Unlimited`,
        field_nickname: `Nickname`,
        field_dialogue_count: `Sample Dialogues`,
        field_attributes: `Attributes`,
        field_is_alter: `Is Alter Persona`,
        field_alter_triggers: `Alter Triggers`,
        field_persona_triggers: `Persona Triggers`,
        field_persona_model: `Persona Model Override`,
        persona_model_server_default: `Server default`,
        field_system_prompt: `System Prompt`,
        field_persona_prompt: `Persona Prompt`,
        field_persona_prompt_not_set: `*(Not set)*`,
        field_nai_tags: `NAI Image Tags`,
        field_nai_attg: `NAI ATTG Metadata`,
        nai_attg_not_set: `*(Not configured)*`,
        field_user_nickname: `User Nickname`,
        field_language_pref: `Language Preference`,
        field_privacy: `Privacy Mode`,
        field_impersonation_prompt: `Impersonation Prompt`,
        field_impersonation_prompt_not_set: `*(Not set)*`,
        field_reminders_count: `Active Reminders`,
        field_personal_memories: `Personal Memories`,
        field_server_memories: `Server Memories`,
        item_count: `{count} items`,
        none: `None`,
        disabled: `Disabled`,
        unknown_channel: `Unknown Channel ID:`,
        not_available: `N/A`,
        see_all_memories_prompt: `Please use the \`/data export\` command to see all memories`,
        memories_omitted: `...and {count} more memories omitted`,
        export_footer: `Use the \`/data export\` command to see full, non-truncated memories`,
        export_footer_full: `Use the \`/data export\` command to see full details on everything`,
        export_footer_global_personal_memories: `Use \`/data export type:global_personal_memories\` to view full values`,
        export_footer_persona_memories: `Use \`/data export type:persona_personal_memories\` and \`/data export type:persona_server_memories\` to view full values`,
        export_footer_persona_attributes_and_dialogues: `Use \`/persona export\` to view full attributes and sample dialogues`,
        export_footer_server_config: `Use \`/data export type:server_config\` to view full values`,
        field_personal_memories_with_count: `Personal Memories ({current} out of {max} slots used)`,
        field_global_personal_memories_with_count: `Global Personal Memory ({current} out of {max} slots used)`,
        field_trigger_words_with_count: `Trigger Words ({current} out of {max} slots used)`,
        field_attributes_with_count: `Attributes ({current} out of {max} slots used)`,
        field_sample_dialogues_with_count: `Sample Dialogues ({current} out of {max} slots used)`,
        field_persona_personal_memories_with_count: `Persona Personal Memories ({current} out of {max} slots used)`,
        field_persona_server_memories_with_count: `Persona Server Memories ({current} out of {max} slots used)`,
        field_slot_usage: `{current} out of {max} slots used`,
        field_server_memories_with_count: `Server Memories ({current} out of {max} slots used)`,
        field_dialogue_count_with_count: `{current} out of {max} slots used`,
        field_blacklisted_members_with_count: `{current} members`,
      },
      comment: {
        description: `Send a comment embed visible in chat but invisible in context.`,
        modal_title: `Create Comment`,
        content_label: `Comment Content`,
        content_placeholder: `Type your comment here...`,
        invalid_channel_title: `Invalid Channel`,
        invalid_channel_description: `This command can only be used in text channels.`,
        footer: `Comment by {user}, invisible in context`,
        success_title: `Comment Posted`,
        success_description: `Your comment has been posted in this channel.`,
      },
      delete: {
        description: `Delete turns or other channel content.`,
        turn: {
          description: `Delete the last persona's turn from the channel.`,
          regenerate_description: `If true, re-trigger the persona after deletion.`,
          select_persona_description: `If true, choose which persona's turn to delete.`,
          no_permission_title: `Permission Denied`,
          no_permission_description: `This command requires Manage Server permission or must be used in a designated RP channel.`,
          already_running_title: `Already Deleting`,
          already_running_description: `A deletion is already in progress for this channel. Please wait.`,
          no_persona_found_title: `No Persona Turn Found`,
          no_persona_found_description: `Couldn't find a contiguous block of persona messages in the recent history.`,
          deleting_title: `⏳ Deleting Turn`,
          deleting_description: `Deleting {count} message(s) from **{persona_name}**...`,
          success_title: `✅ Turn Deleted`,
          success_description: `Deleted {count} message(s) from **{persona_name}**.`,
          success_regenerate_description: `Deleted {count} message(s) from **{persona_name}**. Re-triggering...`,
          partial_title: `⚠️ Partial Deletion`,
          partial_description: `Deleted {deleted_count}/{total_count} message(s) from **{persona_name}**. Some messages could not be deleted.`,
        },
      },
    },

    // Data management commands
    data: {
      description: `Manage your data exports and imports`,
      export: {
        description: `Export specific data to a JSON backup file`,
        type_description: `What do you want to export?`,
        scope_description: `Choose scope for the selected data type`,
        type_choice_personal: `Personal Data`,
        type_choice_server: `Server Data`,
        type_choice_personality: `Personality Info`,
        type_choice_persona_personal_memories: `Personal Memories of Persona`,
        type_choice_persona_server_memories: `Server Memories of Persona`,
        type_choice_personal_settings: `Personal Settings`,
        type_choice_server_config: `Server Config`,
        type_choice_global_personal_memories: `Global Personal Memories`,
        scope_choice_persona: `Persona`,
        scope_choice_global: `Global`,
        scope_choice_serverwide: `Serverwide`,
        persona_modal_title: `Select Persona`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona to export memory data from.`,
        persona_select_placeholder: `Select a persona...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        success_title: `🟢 Export Successful`,
        success_description: `Your {type} data has been sent to your DMs!`,
        success_description_personality: `My personality has been exported and sent to your DMs!\n\n**Note:** This export is for informational purposes only. To import personalities, use the \`/persona\` commands instead.`,
        failed_title: `🔴 Export Failed`,
        failed_description: `Failed to export your data. Please try again later.`,
        dm_title: `Data Export`,
        dm_description: `Here's the {type} data that you requested from me!`,
        dm_description_server: `Here's the server data you requested!\n\n**Note:** Trigger words and API keys are excluded for security. You'll need to reconfigure those manually after import.`,
        dm_description_personality: `Here's the personality information you requested!\n\n**Note:** This text file is for informational purposes only. To import personalities into your server, use the \`/persona\` commands instead.`,
        dm_failed_title: `🔴 Could Not Send DM`,
        dm_failed_description: `I couldn't send you a DM. Please make sure you have DMs enabled from server members, then try again.`,
        no_permission_title: `🔴 Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to export server data.`,
        invalid_scope_title: `🔴 Invalid Scope`,
        invalid_scope_personal_description: `\`serverwide\` scope is not valid for personal data exports.`,
        invalid_scope_server_description: `\`global\` scope is not valid for server data exports.`,
        invalid_scope_personality_description: `Only \`persona\` scope is valid for personality exports.`,
        // Error messages from dataExport utility
        error_no_user_data: `No user data found. You may need to interact with the bot first.`,
        error_no_server_data: `Server not found in database. Please run /config setup first.`,
        error_no_server_config: `Server configuration not found. Please run /config setup first.`,
        error_no_personality_data: `No personality data found for this server. Please run /config setup first.`,
        error_validation_failed: `Failed to validate export data structure`,
        error_export_failed: `Failed to export data`,
      },
      import: {
        description: `Import data from an exported JSON file (auto-detected)`,
        file_description: `The JSON file to import data from`,
        confirmation_description: `WARNING: This may replace existing memories/settings based on file type. Continue?`,
        confirmation_description_server: `WARNING: Replaces server settings & memories. Does NOT restore: trigger words, API keys, personality, avatar.`,
        scope_description: `Choose scope for where imported data is applied`,
        confirmation_choice_yes: `Yes, I understand and want to proceed`,
        confirmation_choice_no: `No, cancel the import`,
        scope_choice_persona: `Persona`,
        scope_choice_global: `Global`,
        scope_choice_serverwide: `Serverwide`,
        persona_modal_title: `Select Persona`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona this import should target.`,
        persona_select_placeholder: `Select a persona...`,
        global_option_label: `Global`,
        global_option_description: `Global means shared memory scope, not persona-specific.`,
        legacy_personal_label: `Legacy Personal Backup`,
        legacy_server_label: `Legacy Server Backup`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        success_title: `🟢 Import Successful`,
        success_description: `Successfully imported {type} data!\nMemories imported: {memories_count}\n Config fields updated: {config_count}`,
        success_description_server: `Successfully imported server data!\nMemories: {memories_count}\n Settings: {config_count}\n\n**Remember:** Trigger words and API keys were not imported. Configure those separately if needed.`,
        success_description_server_persona_scope: `Successfully imported server data for the selected persona scope!\nMemories: {memories_count}\n Settings: {config_count}\n\n**Note:** Server settings are still serverwide. Trigger words and API keys were not imported.`,
        failed_title: `🔴 Import Failed`,
        failed_description: `Failed to import your data. Please check the file and try again.`,
        cancelled_title: `🔴 Import Cancelled`,
        cancelled_description: `The import has been cancelled. No data was changed.`,
        invalid_file_type_title: `🔴 Invalid File Type`,
        invalid_file_type_description: `Please upload a valid .json file.`,
        file_too_large_title: `🔴 File Too Large`,
        file_too_large_description: `The file is too large. Maximum file size is 1MB.`,
        parse_failed_title: `🔴 Invalid JSON`,
        parse_failed_description: `The file is not a valid JSON file. Please check the file format.`,
        invalid_file_title: `🔴 Invalid Import File`,
        invalid_file_description: `The import file format is invalid or incompatible.`,
        no_permission_title: `🔴 Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to import server data.`,
        invalid_scope_title: `🔴 Invalid Scope`,
        invalid_scope_personal_description: `\`serverwide\` scope is not valid for personal imports.`,
        invalid_scope_server_description: `\`global\` scope is not valid for server imports.`,
        error_download_timeout: `File download timed out. Please try again.`,
        error_download_failed: `Failed to download import file.`,
        // Error messages from dataImport utility
        error_invalid_memory: `Invalid memory content: {details}`,
        error_update_failed: `Failed to update user data in database`,
        error_import_failed: `Failed to import data`,
        error_no_server_data: `Server not found in database. Please run /config setup first.`,
        error_invalid_server_memory: `Invalid server memory content: {details}`,
        error_invalid_config: `Invalid configuration fields in import data`,
        error_no_users: `No users found in database. Cannot attribute server memories.`,
        error_not_json: `Import file must contain a valid JSON object`,
        error_incompatible_version: `Incompatible import version. Expected {expected}, got {actual}`,
        error_invalid_personal_format: `Invalid personal import file format`,
        error_invalid_server_format: `Invalid server import file format`,
        error_invalid_personal_memories_format: `Invalid personal memories import file format`,
        error_invalid_server_memories_format: `Invalid server memories import file format`,
        error_invalid_personal_settings_format: `Invalid personal settings import file format`,
        error_invalid_server_config_format: `Invalid server config import file format`,
        error_unknown_type: `Unknown import type: {type}.`,
      },
      delete: {
        description: `Permanently delete selected data scopes`,
        type_description: `What do you want to delete?`,
        scope_description: `Optional scope (leave empty for legacy full delete behavior)`,
        type_choice_personal: `Personal Data`,
        type_choice_server: `Server Data`,
        type_choice_persona_personal_memories: `Personal Memories of Persona`,
        type_choice_persona_server_memories: `Server Memories of Persona`,
        type_choice_personal_settings: `Personal Settings`,
        type_choice_server_config: `Server Config`,
        type_choice_global_personal_memories: `Global Personal Memories`,
        scope_choice_persona: `Persona`,
        scope_choice_global: `Global`,
        scope_choice_serverwide: `Serverwide`,
        confirmation_description: `Confirm permanent deletion (THIS CANNOT BE UNDONE!)`,
        confirmation_yes: `Yes, permanently delete - I understand this cannot be undone`,
        confirmation_no: `No, cancel deletion`,
        persona_modal_title: `Select Persona`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona scope to delete.`,
        persona_select_placeholder: `Select a persona...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        confirmation_required_title: `Confirmation Required`,
        confirmation_required_description: `You must confirm deletion by selecting the confirmation option.`,
        invalid_scope_title: `🔴 Invalid Scope`,
        invalid_scope_personal_description: `\`serverwide\` scope is not valid for personal deletes.`,
        invalid_scope_server_description: `\`global\` scope is not valid for server deletes.`,
        success_memory_scope_title: `🟢 Scoped Memory Deletion Complete`,
        success_persona_memories_description: `Deleted {memory_count} personal memories for persona "{persona_name}".`,
        success_global_memories_description: `Deleted {memory_count} global personal memories.`,
        success_persona_server_memories_description: `Deleted {memory_count} server memories for persona "{persona_name}".`,
        success_personal_title: `🟢 Personal Data Deleted`,
        success_personal_description: `All your personal data has been permanently deleted. You'll start fresh with default settings if you interact with me again.`,
        success_server_title: `🟢 Server Data Deleted`,
        success_server_description: `All server data has been permanently deleted. You'll need to run \`/config setup\` to use me again.`,
        success_personal_settings_title: `🟢 Personal Settings Reset`,
        success_personal_settings_description: `Your personal settings have been reset to defaults.`,
        success_server_config_title: `🟢 Server Config Reset`,
        success_server_config_description: `Server configuration has been reset to defaults.`,
        no_data_title: `🟡️ No Data Found`,
        no_data_description: `You don't have any personal data stored in the database.`,
        no_persona_memories_description: `No personal memories found for persona "{persona_name}".`,
        no_global_memories_description: `No global personal memories found.`,
        no_server_data_title: `🟡 No Server Data Found`,
        no_server_data_description: `This server doesn't have any data stored in the database. Please run \`/config setup\` first.`,
        no_persona_server_memories_description: `No server memories found for persona "{persona_name}".`,
        no_permission_title: `🔴 Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to delete server data.`,
      },
    },

    // Preset commands
    persona: {
      description: `Manage personality presets`,
      name_conflict_title: `🔴 Persona Name Conflict`,
      name_conflict_description: `A persona named **{name}** already exists on this server. Persona names must be unique within a server.`,
      export: {
        description: `Export current personality as a shareable PNG file`,
        export_json_select_label: `Export JSON`,
        export_json_select_description: `Optional: export a readable JSON file`,
        export_json_select_placeholder: `Default: No (PNG export)`,
        export_json_choice_false: `No (PNG export)`,
        export_json_choice_true: `Yes (JSON export)`,
        persona_modal_title: `Select Persona`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona to export.`,
        persona_select_placeholder: `Select a persona...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        success_title: `🟢 Persona Exported Successfully`,
        success_description: `Current persona **{nickname}** has been exported! Share this PNG file with others to spread this personality configuration.`,
        success_description_json: `Current persona **{nickname}** has been exported as a readable JSON file.\n\n**Note:** This JSON export is for reference only and cannot be imported.`,
        json_non_importable_note: `This JSON export is for reference only and cannot be imported.`,
        failed_title: `🔴 Export Failed`,
        failed_description: `Failed to export the persona. Please try again later.`,
        avatar_failed_title: `🔴 Avatar Download Failed`,
        avatar_failed_description: `Failed to download the persona avatar. Please try again later.`,
        embed_failed_title: `🔴 PNG Processing Failed`,
        embed_failed_description: `Failed to embed metadata into the PNG file. Please try again.`,
        // Error messages from presetExport utility
        error_no_server_data: `Server not found in database. Please run /config setup first.`,
        error_no_preset_data: `Persona data not found. Please run /config setup first.`,
        error_validation_failed: `Failed to validate export data structure`,
        error_export_failed: `Failed to export persona data`,
      },
      import: {
        description: `Import a personality from a PNG file`,
        file_description: `PNG file containing persona data`,
        type_description: `Import as main persona or alter persona`,
        triggers_description: `Optional extra triggers, comma-separated ("," or "、")`,
        memories_description: `Preserve this persona's user and server memories?`,
        memories_choice_preserve: `Yes, preserve user/server memories`,
        memories_choice_fork: `No, start fresh user/server memories`,
        type_choice_main: `Main Persona (replaces current persona)`,
        type_choice_alter: `Alter Persona`,
        confirmation_description: `WARNING: This will REPLACE your current personality settings. Continue?`,
        confirmation_choice_yes: `Yes, replace my current persona`,
        confirmation_choice_no: `No, cancel import`,
        success_title: `🟢 Persona Imported Successfully`,
        success_description: `Successfully imported persona **{nickname}**!\nAttributes: {attribute_count}\nSample Dialogues: {dialogue_count}\nTrigger Words: {trigger_word_count}`,
        success_confirmation: `Successfully imported main persona **{nickname}**! The detailed import information has been posted in the channel.`,
        nickname_update_success: `Server nickname has been updated.`,
        nickname_update_failed: `🟡 Server nickname could not be updated, likely due to Discord rate limits. Please change it manually instead.`,
        avatar_update_success: `Server avatar has been updated.`,
        avatar_update_rate_limited: `🟡 Server avatar was not updated due to Discord rate limits. Please change it manually instead.`,
        avatar_update_failed: `🟡 Server avatar could not be updated, likely due to Discord rate limits. Please change it manually instead.`,
        alter_success_title: `🟢 Alter Persona Imported Successfully`,
        alter_success_description: `Successfully imported alter persona **{nickname}**!\nUnique Trigger Words: {trigger_count}\nTriggers: {triggers}\n\nThis persona will respond when these triggers appear in messages.`,
        alter_success_confirmation: `Successfully imported alter persona **{nickname}** with {trigger_count} unique trigger words! The detailed import information has been posted in the channel.`,
        alter_avatar_warning: `⚠️ Do not delete the avatar image embed above, or the alter persona avatar will be lost.`,
        alter_dm_not_allowed_title: `🔴 Alter Personas Not Allowed in DMs`,
        alter_dm_not_allowed_description: `Alter personas can only be imported in servers, not in Direct Messages. Please run this command in a server.`,
        alter_no_triggers_error_title: `🔴 No Unique Triggers`,
        alter_no_triggers_error_description: `All trigger words in this persona already exist in other personas.\nOverlapping triggers: {overlap}\n\nPlease edit the PNG file to add unique trigger words, or remove conflicting personas using \`/persona remove\`.`,
        alter_no_triggers_warning: `⚠️ This persona has no trigger words. It won't respond to any messages until you add triggers using \`/server trigger add\`.`,
        alter_name_conflict_title: `🔴 Persona Name Already Exists`,
        alter_name_conflict_description: `A persona with the name **{name}** already exists on this server. Each persona must have a unique name.\n\nPlease edit the PNG file to use a different name, or remove the existing persona using \`/persona remove\`.`,
        alter_limit_title: `🔴 Persona Limit Reached`,
        alter_limit_description: `This server already has {current} personas. The maximum allowed is {max}. Please remove an alter with \`/persona remove\` before importing a new one.`,
        failed_title: `🔴 Import Failed`,
        failed_description: `Failed to import the persona. Please check the file and try again.`,
        cancelled_title: `🔴 Import Cancelled`,
        cancelled_description: `The import has been cancelled. No changes were made to my persona.`,
        invalid_file_type_title: `🔴 Invalid File Type`,
        invalid_file_type_description: `Please upload a valid .png file containing persona data.`,
        file_too_large_title: `🔴 File Too Large`,
        file_too_large_description: `The file is too large. Maximum file size is 10MB.`,
        download_failed_title: `🔴 Download Failed`,
        download_failed_description: `Failed to download the attached file. Please try again.`,
        invalid_png_title: `🔴 Invalid PNG File`,
        invalid_png_description: `The uploaded file is not a valid PNG image.`,
        no_metadata_title: `🔴 No Persona Data Found`,
        no_metadata_description: `This PNG file doesn't contain persona data. Please use a file exported by \`/persona export\`.`,
        invalid_file_title: `🔴 Invalid Persona File`,
        invalid_file_description: `The persona file format is invalid or incompatible.`,
        no_permission_title: `🔴 Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to import personas.`,
        error_download_timeout: `File download timed out. Please try again.`,
        error_download_failed: `Failed to download preset file.`,
        // Error messages from presetImport utility
        error_invalid_attribute: `Invalid attribute content: {details}`,
        error_invalid_dialogue_in: `Invalid sample dialogue (input): {details}`,
        error_invalid_dialogue_out: `Invalid sample dialogue (output): {details}`,
        error_invalid_trigger_word: `Invalid trigger word: {details}`,
        error_dialogue_mismatch: `Sample dialogue arrays don't match in length`,
        error_invalid_config: `Invalid configuration fields in persona data`,
        error_no_server_data: `Server not found in database. Please run \`/config setup\` first.`,
        error_name_conflict: `A persona with the name **{name}** already exists on this server. Please use a different name.`,
        error_import_failed: `Failed to import persona data`,
        error_not_json: `Preset file must contain valid JSON data`,
        error_incompatible_version: `Incompatible preset version. Expected {expected}, got {actual}`,
        error_invalid_format: `Invalid persona file format`,
        error_invalid_type: `Invalid persona type: {type}. Expected "persona"`,
        avatar_update_skipped_dm: `Preset was imported successfully, except avatar and nickname updates which are not available in Direct Messages`,
        refresh_reminder: `Run \`/tool refresh\` to apply persona update in this chat`,
      },
      remove: {
        description: `Remove an alter persona from the server`,
        confirmation_description: `Confirm scope: removes persona assets and persona-scoped data only.`,
        confirmation_choice_confirm: `Confirm remove (keeps personal user memories)`,
        confirmation_choice_cancel: `Cancel`,
        no_permission_title: `🔴 Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to remove alter personas.`,
        modal_title: `Remove Alter Persona`,
        select_label: `Alter Persona`,
        select_placeholder: `Choose an alter persona to remove...`,
        no_alters_error_title: `🟡 No Alter Personas`,
        no_alters_error_description: `There are no alter personas to remove. Import alter personas using \`/persona import type:alter\`.`,
        success_title: `🟢 Alter Persona Removed`,
        success_description: `Successfully removed alter persona **{nickname}**.`,
      },
      swap: {
        description: `Swap the main persona with an alter persona`,
        no_permission_title: `🔴 Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to swap personas.`,
        modal_title: `Swap Main Persona`,
        select_label: `Alter Persona`,
        select_placeholder: `Choose an alter persona to promote to main...`,
        no_alters_error_title: `🟡 No Alter Personas`,
        no_alters_error_description: `There are no alter personas to swap with. Import alter personas using \`/persona import type:alter\`.`,
        success_title: `🟢 Personas Swapped Successfully`,
        success_description: `**{new_main}** is now the main persona.\n**{old_main}** is now an alter persona.`,
        nickname_update_success: `Server nickname has been updated.`,
        nickname_update_failed: `🟡 Server nickname could not be updated, likely due to Discord rate limits. Please change it manually instead.`,
        avatar_update_success: `Server avatar has been updated.`,
        avatar_update_rate_limited: `🟡 Server avatar was not updated due to Discord rate limits. Please change it manually instead.`,
        avatar_update_failed: `🟡 Server avatar could not be updated, likely due to Discord rate limits. Please change it manually instead.`,
        avatar_embed_warning: `⚠️ Do not delete this embed, or the stored avatar URL may be lost.`,
        avatar_stored_notice: `The former main persona's avatar has been stored for future use.`,
      },
      default: {
        description: `Apply a preset personality configuration`,
        type_description: `Target main/default persona or create as alter persona`,
        type_choice_default: `Default Persona`,
        type_choice_alter: `Alter Persona`,
        no_permission_title: `🔴 Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to apply personality presets.`,
        modal_title: `Apply Personality Preset`,
        select_label: `Personality Preset`,
        select_description: `Choose a preset to apply. This will overwrite current attributes and dialogues.`,
        select_placeholder: `Choose a preset...`,
        no_presets_title: `No Presets Available`,
        no_presets_description: `There are no personality presets available for your language. Please report through \`/support discord\`.`,
        preset_not_found: `The selected preset could not be found.`,
        success_title: `Preset Applied`,
        success_description: `Successfully applied the '{preset_name}' preset.`,
        success_details_description: `Successfully applied preset **{preset_name}** to persona **{nickname}**!\nAttributes: {attribute_count}\nSample Dialogues: {dialogue_count}\nTrigger Words ({trigger_word_count}): {triggers}`,
        success_confirmation: `Preset applied to **{nickname}**. Detailed information has been posted in this channel.`,
        avatar_update_failed: `🟡️ Server avatar could not be updated due to a Discord API error, but persona was applied successfully.`,
        avatar_update_skipped_dm: `Preset was applied successfully, except avatar updates which are not available in Direct Messages`,
      },
      generate: {
        description: `AI-powered personality generation (requires a compatible provider)`,
        // Modal fields
        modal: {
          title: `Generate AI Personality`,
          character_name_label: `Character Name`,
          character_name_description: `Comma-separated names ("," or "、"): all become trigger words; first becomes display name.`,
          character_name_placeholder: `e.g. Hatsune Miku, Miku, 初音ミク`,
          character_info_label: `Character Info & Speech Examples`,
          character_info_description: `Describe the character and how they speak`,
          character_info_placeholder: `Personality, backstory, speech style, example phrases, etc.`,
          web_search_label: `Search the Web?`,
          web_search_description: `Search for character info (for existing characters from media)`,
          web_search_placeholder: `Select Yes or No`,
          web_search_yes: `Yes, search for character information`,
          web_search_no: `No, create original character`,
          additional_inst_label: `Additional Instructions`,
          additional_inst_placeholder: `Optional: Other instructions (e.g., "please keep the character's responses short")`,
          file_upload_label: `Character Image / Card (Optional)`,
          file_upload_description: `Upload an image, Tomori preset, or SillyTavern card PNG to generate or transform a character`,
        },
        // Field labels for memory critical error preservation
        field_character_name: `Character Name`,
        field_character_info: `Character Info & Speech Examples`,
        field_web_search: `Search the Web?`,
        field_additional_inst: `Additional Instructions`,
        // Error messages
        wrong_provider_title: `🔴 Incompatible Provider`,
        wrong_provider_description: `Preset generation requires a compatible provider. Your current provider is **{current_provider}**. Please use \`/config apikey set\` to switch providers.`,
        no_api_key_title: `🔴 No API Key`,
        no_api_key_description: `No API key configured. Please use \`/config apikey set\` to set up your provider API key.`,
        model_incompatible_title: `Incompatible Model`,
        model_incompatible_description: `Your current model (**{model_name}**) does not support **STRUCTURED OUTPUT**, which is required for persona generation.\n\n**Next steps:**\nUse \`/config model text\` to switch to a model that supports structured output (e.g., models with "STRUCT" capability).`,
        image_vision_required_title: `🔴 Image Vision Required`,
        image_vision_required_description: `You uploaded an image, but your current model (**{model_name}**) does not support **IMAGE VISION** and no vision model is configured.\n\n**Next steps:**\n1. Use \`/config model vision\` to set a dedicated vision model, OR\n2. Use \`/config model text\` to switch to a vision-capable model, OR\n3. Remove the image and regenerate without it`,
        vision_model_provider_unsupported_title: `🔴 Vision Model Provider Unsupported`,
        vision_model_provider_unsupported_description: `Your vision model (**{vision_model_name}**) is on provider **{vision_provider}**, which does not support persona preset generation.\n\n**Next steps:**\n1. Use \`/config model vision\` to set a vision model from a supported provider (Google, OpenRouter, DeepSeek, Z.ai, Custom, NVIDIA NIM), OR\n2. Use \`/config model text\` to switch your primary model to one that supports both vision and preset generation`,
        web_search_tools_required_title: `🔴 Web Search Unavailable`,
        web_search_tools_required_description: `You selected web search, but the current model (**{model_name}**) does not support **TOOLS**.\n\n**Next steps:**\n1. Use \`/config model text\` to switch to a tool-enabled model, OR\n2. Regenerate without web search (choose "No" when asked)`,
        api_key_decrypt_failed_title: `🔴 API Key Error`,
        api_key_decrypt_failed_description: `Failed to decrypt API key. Please reconfigure using \`/config apikey set\`.`,
        invalid_image_title: `🔴 Invalid Image`,
        invalid_image_description: `Please upload a valid image file (PNG, JPG, JPEG, etc.).`,
        image_download_failed_title: `🔴 Image Download Failed`,
        image_download_failed_description: `Failed to download the attached image. Please try again.`,
        error_file_too_large: `Avatar image must be under 10 MB.`,
        error_download_timeout: `Avatar download timed out. Please try again.`,
        error_download_failed: `Failed to download avatar image.`,

        // Processing
        processing_title: `Generating Personality...`,
        processing_description: `This may take 1-2 minutes. Please wait while I generate the character...\n\nThis may produce unexpected results. You can regenerate if needed.`,
        // Generation errors
        generation_failed_title: `🔴 Generation Failed`,
        generation_failed_description: `Failed to generate personality: {error}\n\nPlease try again with different inputs or check your API key.`,
        validation_failed_title: `🔴 Validation Failed`,
        validation_failed_description: `The generated personality data failed validation. Please try again.`,
        image_processing_failed_title: `🔴 Image Processing Failed`,
        image_processing_failed_description: `Failed to process the uploaded image. Please try a different image.`,
        avatar_fetch_failed_title: `🔴 Avatar Fetch Failed`,
        avatar_fetch_failed_description: `Failed to fetch the server avatar for export. Please try uploading an image instead.`,
        metadata_embed_failed_title: `🔴 Export Failed`,
        metadata_embed_failed_description: `Failed to embed personality data in the image. Please try again.`,
        // Success
        success_title: `🟢 {character_name} Generated Successfully!`,
        success_description: `I've generated a persona for **{character_name}**!\n**Attributes Preview:**\n{attribute_preview}\n**Sample Dialogues:**\n{dialogue_preview}`,
        success_next_steps_title: `Next Steps`,
        success_next_steps_description: `1. Download the attached PNG file\n2. Use \`/persona import\` with the PNG to import this character\n3. Run \`/tool refresh\` on ongoing conversations to apply my new personality\n4. (Optional) Use \`/server avatar\` to change the avatar if desired`,
        avatar_update_skipped_dm: `Please note that avatar and nickname updates are not available to import in Direct Messages.`,
      },
      create: {
        description: `Create a simple personality preset manually`,
        // Modal fields
        modal: {
          title: `Create Persona`,
          character_name_label: `Character Name`,
          character_name_description: `Comma-separated names ("," or "、"): all become trigger words; first becomes display name.`,
          character_name_placeholder: `e.g. Hatsune Miku, Miku, 初音ミク`,
          character_desc_label: `Character Description`,
          character_desc_placeholder: `Describe your character (personality, appearance, backstory, etc.)`,
          example_user_label: `Example User Message`,
          example_user_description: `Tip: Add more using /teach sampledialogue after`,
          example_user_placeholder: `Hi {bot}!`,
          example_bot_label: `Example Bot Reply`,
          example_bot_placeholder: `Hello {user}! You doing good?`,
          file_upload_label: `Character Image (Optional)`,
          file_upload_description: `Upload an image for the character export`,
        },
        // Field labels for memory critical error preservation
        field_character_name: `Character Name`,
        field_character_desc: `Character Description`,
        field_example_user: `Example User Message`,
        field_example_bot: `Example Bot Reply`,
        // Error messages
        invalid_image_title: `🔴 Invalid Image`,
        invalid_image_description: `Please upload a valid image file (PNG, JPG, JPEG, etc.).`,
        image_download_failed_title: `🔴 Image Download Failed`,
        image_download_failed_description: `Failed to download the attached image. Please try again.`,
        error_file_too_large: `Avatar image must be under 10 MB.`,
        error_download_timeout: `Avatar download timed out. Please try again.`,
        error_download_failed: `Failed to download avatar image.`,

        desc_too_long_title: `Description Too Long`,
        desc_too_long_description: `The character description is too long ({current_length} characters). Maximum allowed length is {max_allowed} characters.`,
        example_user_too_long_title: `Example User Message Too Long`,
        example_user_too_long_description: `The example user message is too long ({current_length} characters). Maximum allowed length is {max_allowed} characters.`,
        example_bot_too_long_title: `Example Bot Reply Too Long`,
        example_bot_too_long_description: `The example bot reply is too long ({current_length} characters). Maximum allowed length is {max_allowed} characters.`,

        validation_failed_title: `🔴 Validation Failed`,
        validation_failed_description: `The preset data failed validation. Please try again.`,
        image_processing_failed_title: `🔴 Image Processing Failed`,
        image_processing_failed_description: `Failed to process the uploaded image. Please try a different image.`,
        avatar_fetch_failed_title: `🔴 Avatar Fetch Failed`,
        avatar_fetch_failed_description: `Failed to fetch the server avatar for export. Please try uploading an image instead.`,
        metadata_embed_failed_title: `🔴 Export Failed`,
        metadata_embed_failed_description: `Failed to embed personality data in the image. Please try again.`,
        // Success
        success_title: `🟢 {character_name} Created Successfully!`,
        success_description: `Persona has been created for **{character_name}**!\n**Description:**\n{character_description}`,
        success_dialogue_title: `Sample Dialogue`,
        success_next_steps_title: `Next Steps`,
        success_next_steps_description: `1. Download the attached PNG file\n2. Use \`/persona import\` with the PNG to import this character\n3. Run \`/tool refresh\` on ongoing conversations to apply my new personality\n4. (Optional) Use \`/server avatar\` to change the avatar if desired`,
        avatar_update_skipped_dm: `Please note that avatar and nickname updates are not available in Direct Messages.`,
      },
    },

    // Help commands
    help: {
      // /help features
      features: {
        description: `Shows what TomoriBot can do`,
        title: `TomoriBot Features (Version {version})`,
        embed_description: `Here's everything I'm capable of:`,
        vision_title: `Vision & Media`,
        vision_description: `- I can see and analyze images, videos, stickers, and emojis
- I can watch YouTube videos from links
- I can see content within shared embeds (like tweets, articles, etc.)`,
        search_title: `Search & Information`,
        search_description: `- I can search the web for current information
- I can also do image, video, and news search (via \`/optionalkey brave set\`)
- I can fetch and read content from URLs`,
        personality_title: `Personality & Customization`,
        personality_description: `- I can change my name and avatar using \`/config rename\` and \`/server avatar\`
- I can switch between different personas using \`/persona\` (you can also share and save personas using \`/persona export\`!)
- Multiple characters can coexist as alter personas, each with their own triggers and webhook avatar
- My behavior and tone can be tweaked with \`/teach\`
- A custom system prompt can be set with \`/config sysprompt\` to further shape my behavior
- Learn more with \`/help customization\``,
        memory_title: `Memory & Personalization`,
        memory_description: `- I can remember personal facts about you and server-wide information, persisting across conversations
- Personal memories persist across servers (try talking to me in another server!)
- I also keep STM (short-term memory) of recent conversations for channel and server awareness (opt into cross-server sharing with \`/personal stm\`)
- Change what I call you using \`/personal nickname\`
- Use \`/teach\` to manually help me remember things, \`/forget\` to remove them
- I can use server emojis and stickers more accurately after registration with \`/server initialize expressions\`
- Full invisibility is available via \`/personal privacy\` if you want to be completely unseen by me
- Learn more with \`/help memory\``,
        time_title: `Time Awareness`,
        time_description: `- I know what time it currently is in the server (via \`/config timezone\`)
- I can set up reminders for you (try asking me to remind you about something!)
- Recurrent reminders and tasks are supported and are persona-specific, just tell me to do something`,
        alter_title: `Alter Personas`,
        alter_description: `- Multiple characters can coexist in one server via alter personas
- Each alter has its own personality and is triggered by specific keywords
- Alter personas use webhooks for distinct avatars
- Multiple alters can respond to a single message (up to the \`/config multitrigger\` limit)
- Replying to a webhook message continues the conversation as that persona
- Manage alters with \`/persona import\` (alter option) and \`/persona remove\``,
        expressions_title: `Expressions & Reactions`,
        expressions_description: `- I can use your server's custom emojis naturally in conversation (case-insensitive \`:name:\` syntax)
- I can send stickers as part of my replies
- I can react to messages with relevant emojis
- Register emojis and stickers with \`/server initialize expressions\` for higher accuracy`,
        documents_title: `Document Knowledge Base`,
        documents_description: `- Upload text, PDF, or Markdown files as server knowledge using \`/teach document\`
- I retrieve and reference relevant document content when answering questions
- I can also read document attachments (PDF, TXT, MD) shared directly in chat, just ask me to read it!
- Requires an embedding model (configure with \`/config model embedding\`)
- Remove documents with \`/forget document\``,
        impersonation_title: `Impersonation & Tools`,
        impersonation_description: `- Use \`/bot impersonate\` to send messages as yourself, a persona, or inject system messages
- Set a reusable user-impersonation persona prompt with \`/personal impersonate prompt\`
- \`/tools compact\` can summarize or roleplay-compress conversation history
- \`/bot respond\` to trigger prefilled or guided messages from the bot`,
        imagegen_title: `Image Generation`,
        imagegen_description: `- I can generate images from text prompts or by editing reference images
- Supports Text2Image and Image2Image with customizable aspect ratios
- Use \`/generate image\` or just ask me to generate an image
- Reference images can come from message attachments, stickers, emojis, or user avatars
- Available on Google, OpenRouter, Z.ai, Z.ai (Coding), and NVIDIA NIM providers (configure with \`/config model image\`)`,
        footer: `Not all features are available for all AI providers. Recommended: Google Gemini. You can also just ask me what I can do!`,
      },

      // /help cost
      cost: {
        description: `Estimate API costs for paid AI providers`,
        title: `Estimated API Costs`,
        embed_description: `Here are **VERY ROUGH** estimated costs per trigger in a Discord channel when using paid AI providers. Costs are estimated using example **{provider}** costs (Input: {inputPrice}/M tokens, Output: {outputPrice}/M tokens)`,
        current_context_description: `Estimated cost for your **current context only**. Input tokens are measured by the provider API using your current setup and recent channel history on **{provider}** model **{model}**. Output tokens remain estimated. Pricing used: Input {inputPrice}/M, Output {outputPrice}/M.`,
        current_input_title: `Measured Input Tokens (Current Context)`,
        current_input_value: `**Input:** {inputTokens} tokens\n**Input cost only:** ~{inputCost} per trigger`,
        current_output_short_title: `Estimated Output: Short`,
        current_output_typical_title: `Estimated Output: Typical`,
        current_output_long_title: `Estimated Output: Long`,
        current_output_band_value: `**Output estimate:** {outputTokens} tokens\n**Total estimate:** {totalTokens} tokens\n**Cost:** ~{costPerMessage} per trigger (~{costPer100} per 100 triggers)`,
        current_footer: `Input token counts are provider-measured only for providers with live counting support. Output token counts are estimated only.`,
        fallback_notice_title: `Live Counting Unavailable`,
        fallback_notice_value: `Live provider token counting could not be used for your current setup, so this view is a rough fallback estimate.`,
        minimum_scenario_title: `Minimum Scenario (Light Usage)`,
        minimum_scenario_value: `**Context:** 1 user with 0 memories, 1 paragraph of persona, conversations are less than a sentence per message
**Tokens:** {inputTokens} input + {outputTokens} output = {totalTokens} total
**Cost:** ~{costPerMessage} per trigger (~{costPer100} per 100 triggers)`,
        average_scenario_title: `Average Scenario (Moderate Usage)`,
        average_scenario_value: `**Context:** 3 users with 10 memories each, ~16 paragraphs of persona (includes attributes & dialogues), conversations are 1-2 sentences per message
**Tokens:** {inputTokens} input + {outputTokens} output = {totalTokens} total
**Cost:** ~{costPerMessage} per trigger (~{costPer100} per 100 triggers)`,
        maximum_scenario_title: `Maximum Scenario (Heavy Usage)`,
        maximum_scenario_value: `**Context:** 5 users with 25 memories each, ~31 paragraphs of persona (includes attributes & dialogues), conversations are 2 paragraphs per message
**Tokens:** {inputTokens} input + {outputTokens} output = {totalTokens} total
**Cost:** ~{costPerMessage} per trigger (~{costPer100} per 100 triggers)`,
        breakdown_title: `What Affects Cost?`,
        breakdown_value: `**Input tokens (context sent to AI):**
- Persona paragraphs (includes attributes & sample dialogues)
- Server & personal memories
- Enabled tools (if any)
- User statuses & reminders
- Recent conversation history (includes images, videos, stickers, emojis, embeds if provider supports)
- Server emojis (10 constant)

**Output tokens (AI response):**
- Response length varies by query complexity
- More detailed questions = longer responses = higher cost

**Tips to reduce costs:**
I have built-in features to help reduce costs from abusers or spammers in your server, but here are some additional tips:
- Use fewer persona paragraphs (attributes & dialogues)
- Keep memories concise
- Use free AI providers (Google Gemini free tier)
- Limit auto-trigger channels`,
        footer: `Free providers like Google Gemini (free tier) and some OpenRouter models have no cost! NovelAI offers unlimited usage with a subscription. Use \`/help apikey\` to learn more.`,
      },

      // /help setup
      setup: {
        description: `Learn how to set up TomoriBot for the first time`,
        title: `Getting Started with TomoriBot`,
        embed_description: `Here's how to set up TomoriBot in your server (or DMs!):`,
        step1_title: `Step 1: Get an API Key`,
        step1_description: `TomoriBot uses AI providers like Google Gemini, NovelAI, or OpenRouter. You'll need an API key from one of them.
- Use {helpApikey} to learn how to get one
  - Google's Gemini = general-purpose, free, and can run all features
  - NovelAI = uncensored role-playing and storytelling specialized
  - OpenRouter = various available AI models
- Do **NOT** share this API key with anyone else`,
        step2_title: `Step 2: Run the Setup Command`,
        step2_description: `- Use {configSetup} to securely add your API key and initialize TomoriBot
- (Recommended) Run {serverInitializeExpressions} so I can properly use your server's emojis/stickers
	- Your API key is encrypted and stored safely
	- Each server has its own configuration`,
        step3_title: `Step 3: Start Chatting!`,
        step3_description: `- Just mention me or reply to my messages to chat
- Change how I get triggered using {serverTrigger}
- I'll remember our conversations with my memory system (which you can disable using {configPermissions}!)
- Set up auto-trigger with {serverAutotrigger} to chat without mentioning me`,
        step4_title: `Optional: Customize Me`,
        step4_description: `- Use {persona} commands to completely change my personality (including alter personas!)
- Configure my settings with {server}, {personal}, and {config} commands
- You can also manually teach me things with {teach}
- Explore advanced features like document uploads, API key rotation, and uncensored mode`,
        need_help_title: `Need Help?`,
        need_help_description: `- {helpFeatures} - See what I can do
- {helpMemory} - Learn about my memory system
- {helpCustomization} - Learn about personality customization
- {supportServer} - Join the official TomoriBot support server

Setting up TomoriBot means that you and your server members agree to its \`/legal terms\` and \`/legal privacy\` notices`,
      },

      // /help matrix
      matrix: {
        description: `Learn how to set up and use the Matrix bridge`,
        title: `Matrix Bridge Guide`,
        embed_description: `How to link a Matrix room to a Discord channel, and what currently works from Matrix.`,
        bot_user_fallback: `the configured Matrix bot account`,
        setup_title: `Setup`,
        setup_description: `1. Invite {botUserId} to an unencrypted Matrix room.
2. Copy that room's Internal Room ID.
3. Run {serverMatrixLink} in the Discord channel you want to bridge and paste the room ID there.`,
        room_id_title: `Finding the Room ID`,
        room_id_description: `In most Matrix clients, open Room Settings -> Advanced -> Internal Room ID.
The ID looks like \`!abc:matrix.org\`.

After the bot accepts an invite, it now posts a short reminder in the Matrix room, but you still need to finish the link from Discord with {serverMatrixLink}.`,
        usage_title: `Using It From Matrix`,
        usage_description: `- Talk in Matrix normally after the room is linked
- Matrix messages relay into the linked Discord channel as webhook messages
- TomoriBot replies back into the Matrix room
- The only Matrix text commands are /kill and /refresh`,
        limitations_title: `Current Limitations`,
        limitations_description: `- No slash commands from Matrix
- No DMs / DM-based cooldown reminders
- Matrix user profile pictures are not visible to TomoriBot
- Cannot pin messages
- Custom emojis and Markdown do not render reliably
- Embeds relay as plain text
- Personal memories for Matrix users fall back to attributed server memories`,
        troubleshooting_title: `Important Notes`,
        troubleshooting_description: `- If the bot does not auto-join, invite {botUserId} manually and rerun {serverMatrixLink} if needed
- Matrix encryption cannot be disabled later, so encrypted rooms must be replaced with a fresh unencrypted room
- If a limitation is not listed above, assume it should work and report bugs in {supportServer}`,
      },

      // /help data
      data: {
        description: `Learn about data management and privacy`,
        title: `Managing Your Data`,
        embed_description: `How you can manage your data and what I store:`,
        export_title: `Export Your Data`,
        export_description: `Use {dataExport} to download your data:
- **Personal Memories of Persona**: Personal memories for one selected persona scope
- **Server Memories of Persona**: Server memories for one selected persona
- **Personal Settings**: Your nickname/language preferences
- **Server Config**: Server configuration values (no API keys/triggers)
- **Global Personal Memories**: Global personal memory scope
- Data is sent to your DMs as a JSON file`,
        import_title: `Import Your Data`,
        import_description: `Use {dataImport} to restore previously exported data:
- File type is auto-detected from the export file
- For memory files, you'll choose a target persona or Global scope
- Server-related imports require \`Manage Server\` in guilds
- Simply attach your exported file when using the command`,
        delete_title: `Delete Your Data`,
        delete_description: `Use {dataDelete} to permanently remove your data:
- **Personal Memories of Persona** / **Global Personal Memories**
- **Server Memories of Persona**
- **Personal Settings** / **Server Config reset**
- This action cannot be undone!`,
        privacy_title: `Privacy Notice`,
        privacy_description: `**What I Store:**
- Server/personal memories
- My settings and persona
- My server configurations
- Encrypted API keys

**What I Do NOT Store:**
- Your Discord messages
- Chat History

**What is Sent to your Chosen AI Provider:**
Whenever I'm triggered, I fetch the **latest messages** in the text channel as well as any **relevant memories** as context for the AI model to form my reply. I do NOT actively monitor and look at messages outside of these triggers.

You may opt out of my Memory features by using the {personalPrivacy} command, as well as turn off my self-learning using the {configPermissions} command.`,
        footer: `Your chosen AI provider (Google, NovelAI, OpenRouter) processes your messages according to their own privacy policies. Never share personal information with me for privacy. For full details, see \`/legal privacy\` and \`/legal terms\``,
      },

      // /help apikey
      apikey: {
        description: `Learn how to set up API keys for AI providers`,
        provider_description: `Choose your AI provider`,
        provider_choice_brave: `Brave Search`,
        provider_choice_google: `Google Gemini`,
        provider_choice_deepseek: `DeepSeek`,
        provider_choice_nvidia: `NVIDIA NIM`,
        provider_choice_novelai: `NovelAI`,
        provider_choice_openrouter: `OpenRouter`,
        provider_choice_zai: `Z.ai`,
        provider_choice_zaicoding: `Z.ai (Coding)`,
        provider_choice_vertex: `Google Vertex AI`,
        provider_choice_elevenlabs: `ElevenLabs TTS`,
        // Brave Search
        brave_title: `Setting Up Brave Search API Key`,
        brave_description: `Brave Search is optional and only enhances my search capabilities. It does NOT power my AI as that's handled by your main provider.
- Enables image, video, and news search
- Provides real-time information from the internet
- Enhances my ability to answer current questions
- Free Tier includes 2,000 queries per month`,
        brave_getting_key_title: `Getting Your API Key:`,
        brave_getting_key_description: `1. Visit [Brave Search API](https://brave.com/search/api/)
2. Sign up for a free account
3. Navigate to your [API Keys](https://api-dashboard.search.brave.com/app/keys) section in the Dashboard
4. Create a new API key
5. Copy and input your API key using the {configBraveapiSet} command`,
        brave_important_title: `Important Notes:`,
        brave_important_description: `- This is separate from your main AI provider
- Without Brave API key, I can still function and use built-in web search`,
        brave_footer: `For setting up your main AI provider, use the other \`/help apikey\` options`,
        // Google Gemini
        google_title: `Setting Up Google Gemini API Key`,
        google_description: `Google Gemini offers free and paid tiers with powerful AI models.
- Free tier available with generous limits
- Supports all TomoriBot features such as vision and persona generation
- [Gemini Privacy Policy](https://ai.google.dev/gemini-api/terms)`,
        google_getting_key_title: `Getting Your API Key:`,
        google_getting_key_description: `1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Click \`Create API Key\` on the top-right (create a new Project if needed)
3. Copy this API key into {configSetup} or {configApikeySet}`,
        google_footer: `After setting up this provider, you may change its default model with {configModel}`,
        // DeepSeek
        deepseek_title: `Setting Up DeepSeek API Key`,
        deepseek_description: `DeepSeek provides direct access to its own chat and reasoning models on a cheap pay-as-you-go basis.
- Supports DeepSeek chat and reasoning models in TomoriBot
- Supports tool-capable and structured-output-capable text models in TomoriBot
- Native image generation and embeddings are not currently available through TomoriBot's DeepSeek provider
- [DeepSeek API Docs](https://api-docs.deepseek.com/)`,
        deepseek_getting_key_title: `Getting Your API Key:`,
        deepseek_getting_key_description: `1. Visit [DeepSeek API Keys](https://platform.deepseek.com/api_keys)
2. Sign in or create a DeepSeek platform account
3. Create a new API key
4. If needed, add credits in your DeepSeek platform account before use
5. Copy this API key into {configSetup} or {configApikeySet}`,
        deepseek_model_notes_title: `Model Notes:`,
        deepseek_model_notes_description: `- \`deepseek-chat\` is the general chat model
- \`deepseek-reasoner\` is the thinking/reasoning model and may respond more slowly
- You can switch between available DeepSeek text models after setup`,
        deepseek_footer: `After setting up this provider, you may change its default model with {configModel}`,
        // NVIDIA NIM
        nvidia_title: `Setting Up NVIDIA NIM API Key`,
        nvidia_description: `NVIDIA NIM provides free hosted chat, embeddings, and image generation through NVIDIA's API catalog.
- Chat and embeddings use NVIDIA's hosted \`integrate.api.nvidia.com\` surface
- Native image generation uses NVIDIA's hosted \`ai.api.nvidia.com\` Stability endpoint
- Structured output and history extraction are available only on supported NVIDIA text models`,
        nvidia_getting_key_title: `Getting Your API Key:`,
        nvidia_getting_key_description: `1. Visit [NVIDIA Build](https://build.nvidia.com/)
2. Sign in or create an NVIDIA developer account
3. Create or manage your API keys from the [API Keys page](https://build.nvidia.com/settings/api-keys)
4. Copy this API key into {configSetup} or {configApikeySet}`,
        nvidia_model_notes_title: `Model Notes:`,
        nvidia_model_notes_description: `- \`deepseek-ai/deepseek-v3.2\` is the default general chat model
- \`qwen/qwen3.5-397b-a17b\` is the highest-capability multimodal model in TomoriBot's curated NVIDIA set
- \`nv-embed-v1\` is the default embedding model
- \`stabilityai/stable-diffusion-3-medium\` is the default NVIDIA image model`,
        nvidia_footer: `After setting up this provider, you may change text, embedding, and image models with {configModel}, {configModelEmbedding}, and {configModelImage}`,
        // Z.ai
        zai_title: `Setting Up Z.ai API Key`,
        zai_description: `Z.ai provides access to the GLM model family with both general API and a dedicated coding endpoint.
- Supports chat, reasoning, image generation, and coding workflows
- GLM models include vision and reasoning variants
- Native image generation via \`glm-image\`
- Tool calling and structured output on all chat models
- Optional MCP add-ons available via \`/config mcp add\` for extra image/video workflows`,
        zai_general_endpoint_title: `General API Endpoint:`,
        zai_general_endpoint_description: `The general Z.ai endpoint provides access to chat, reasoning, and image generation.
- Best for general AI usage and broad compatibility
- Supports all GLM chat models with vision and reasoning capabilities`,
        zai_coding_endpoint_title: `Coding Endpoint:`,
        zai_coding_endpoint_description: `The dedicated Coding endpoint is optimized for GLM Coding Plan and coding-tool workflows.
- Uses a separate endpoint with potentially different billing and access patterns
- If you need standard API billing and broader general usage, use the general endpoint`,
        zai_getting_key_title: `Getting Your API Key:`,
        zai_getting_key_description: `1. Visit the [Z.ai Platform](https://z.ai)
2. Sign in or create an account
3. Navigate to API Keys in your dashboard
4. Create a new API key
5. Copy this API key into {configSetup} or {configApikeySet}`,
        zai_model_notes_title: `Model Notes:`,
        zai_model_notes_description: `- \`glm-5.1\` is the most capable model with advanced reasoning
- \`glm-4.7-flash\` is a free alternative to the default
- \`glm-4.6v\` is the vision-capable model that can see images
- \`glm-image\` generates images from text prompts`,
        zai_footer: `After setting up this provider, you may change its default model with {configModel}`,
        // NovelAI
        novelai_title: `Setting Up NovelAI API Key`,
        novelai_description: `NovelAI is a subscription-based service focused on creative storytelling and roleplay.
- Unlimited uncensored messages
- Currently only supports text generation (no vision or assistant features)
- [NovelAI Terms of Service](https://novelai.net/terms)`,
        novelai_getting_key_title: `Getting Your API Key:`,
        novelai_getting_key_description: `1. Visit [NovelAI](https://novelai.net/stories)
2. Navigate to settings through the ⚙️ icon on the top-left
3. Go to \`Account\`
4. Look for \`Get Persistent API Token\` (subscription required!)
5. Copy this API key into {configSetup} or {configApikeySet}`,
        novelai_footer: `After setting up this provider, you may change its default model with {configModel}`,
        // OpenRouter
        openrouter_title: `Setting Up OpenRouter API Key`,
        openrouter_description: `OpenRouter provides access to multiple AI models from different providers on a pay-as-you-go basis.
- Access to latest and most powerful AI models (some are free)
- Currently does not support all TomoriBot features
- [OpenRouter Terms of Service](https://openrouter.ai/terms)`,
        openrouter_getting_key_title: `Getting Your API Key:`,
        openrouter_getting_key_description: `1. Visit [OpenRouter](https://openrouter.ai/settings/keys)
2. Click \`Create API Key\`
3. Copy this API key {configSetup} or {configApikeySet}`,
        openrouter_model_selection_title: `Choosing Models:`,
        openrouter_model_selection_description: `OpenRouter offers access to many different AI models.
- Currently available models are based on popularity and performance, with tags for distinction:
  - (TOOLS) = Supports tool usage (web search, self-learning, stickers, etc.)
  - (IMG) = Sees images
  - (VID) = Sees videos
  - (STRUCT) = Supports structured output (needed for persona generation and expression initialization)
  - (REASON) = Reasoning / thinking-focused model
  - (FREE) = No cost, but may have rate limits
- If you can't find what you want, try using the \`other-model\` provider option
- Suggest additional models in {supportServer}`,
        openrouter_pricing_title: `Important Pricing Notes:`,
        openrouter_pricing_description: `- **Free models have strict rate limits** - paid models are recommended for better reliability
- **Always check pricing** on OpenRouter before selecting a model to avoid unexpected costs
- Costs vary significantly between models`,
        openrouter_settings_title: `OpenRouter Account Settings:`,
        openrouter_settings_description: `Settings configured in your OpenRouter account (such as model preferences, rate limits, etc.) will also apply when using TomoriBot`,
        openrouter_footer: `After setting up this provider, you may change its default model with {configModel}`,
        // Vertex AI
        vertex_title: `Setting Up Google Vertex AI`,
        vertex_description: `Google Vertex AI provides enterprise-grade access to Gemini models through Google Cloud.
- Uses Application Default Credentials (ADC) for authentication — no API key to manage
- Supports chat, tool calling, streaming, structured output, compaction, embeddings, and preset generation
- Best for self-hosted or trusted deployments where the bot runs with a GCP identity
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)`,
        vertex_getting_key_title: `Configuration:`,
        vertex_getting_key_description: `1. Ensure you have a Google Cloud project with the Vertex AI API enabled
2. Set up Application Default Credentials on the host machine:
   - **Service account**: Attach a service account to your VM/container with Vertex AI access
   - **Local dev**: Run \`gcloud auth application-default login\`
   - **Env var**: Set \`GOOGLE_APPLICATION_CREDENTIALS\` to your service account key file
3. Enter your configuration as \`{project_id}::{location}\` using {configSetup} or {configApikeySet}
   - Example: \`my-gcp-project::us-central1\``,
        vertex_important_title: `Important Notes:`,
        vertex_important_description: `- The stored value is **configuration** (project + location), not a credential secret
- All Vertex requests use the host's ADC identity — there is no per-server credential isolation
- This provider is intended for self-hosted or trusted private deployments
- Supports chat, tool calling, streaming, structured output, compaction, embeddings, and preset generation`,
        vertex_footer: `After setting up this provider, you may change its default model with {configModel}`,
      },

      // /help elevenlabs
      elevenlabs: {
        description: `Learn how to set up ElevenLabs text-to-speech`,
        title: `Setting Up ElevenLabs TTS`,
        what_is_title: `What is ElevenLabs?`,
        what_is_description: `ElevenLabs is an optional text-to-speech (TTS) provider that lets me speak to you using realistic AI-generated voices.
- High-quality voice synthesis with many voice options
- Works alongside any main AI provider
- Free tier available with monthly character limits
- [ElevenLabs Pricing](https://elevenlabs.io/pricing)`,
        getting_key_title: `Getting Your API Key:`,
        getting_key_description: `1. Visit [ElevenLabs](https://elevenlabs.io/app/settings/api-keys)
2. Sign up or sign in to your account
3. Create a new API key
4. Copy this API key using {optionalkeyElevenlabsSet}`,
        choosing_voice_title: `Choosing a Voice:`,
        choosing_voice_description: `After setting up your API key, you can select which voice I use.
- Use {configVoiceElevenlabs} to browse and select from available voices
- Voices include different genders, ages, and accents
- You can always change or remove the voice selection`,
        free_voices_title: `Premade Voices (Free Tier):`,
        free_voices_description: `Premade voices work on the free plan. Browse the full list at [ElevenLabs Premade Voices](https://elevenlabs-sdk.mintlify.app/voices/premade-voices), then use {configVoiceElevenlabs} to assign one to each persona.`,
        important_notes_title: `Important Notes:`,
        important_notes_description: `- ElevenLabs is optional - I can still respond via text
- Characters are counted when I generate voice messages
- Free tier has monthly limits - check your usage on ElevenLabs dashboard
- Remove your API key anytime using {optionalkeyElevenlabsRemove}`,
        footer: `Remove your API key anytime using {optionalkeyElevenlabsRemove}`,
      },

      // /help memory
      memory: {
        description: `Learn about TomoriBot's memory system`,
        title: `How My Memory Works`,
        embed_description: `I have a persistent memory system that helps me remember facts and information about users and servers across conversations. This is about **what I know** (facts, context, information). For **how I behave** (personality, tone, settings), see {helpCustomization} instead!`,
        teaching_title: `Teaching Me Things`,
        teaching_description: `Use {teach} to help me remember **facts and information**:
- **Personal memories** ({teachMemoryPersonal}): Facts about individual users
  - Example: "Amaori loves cats", "Prefers dark mode", "Is allergic to peanuts"
- **Server memories** ({teachMemoryServer}): Information relevant to the whole server
  - Example: "Game night is every Friday at 8 PM", "No posting of NSFW", "We use #general for announcements"`,
        forgetting_title: `Forgetting Things`,
        forgetting_description: `Use {forget} to make me forget memories:
- {forgetMemoryPersonal} - Remove personal facts about users
- {forgetMemoryServer} - Remove server-wide information`,
        how_it_works_title: `How It Works:`,
        how_it_works_description: `- **Personal memories** are tied to you specifically across all servers which I only keep in mind when replying in conversations you are actively participating in
- **Server memories** only stay within the server, I always keep them in mind when replying in a conversation within the server
- Memories persist until you use the \`/forget\` command on them`,
        tips_title: `Memory Tips:`,
        tips_description: `- Teach me your preferences, nicknames, and important facts
- Use server memories for shared information, inside jokes, or server rules
- Review your memories periodically with {dataExport} or {status}
- Keep memories concise and clear for best results

**Privacy:** See \`/legal privacy\` for full data handling details`,
        documents_title: `Document Knowledge Base`,
        documents_description: `Server administrators can upload documents for me to reference:
- Use \`/teach document\` to upload text, PDF, or Markdown files
- Documents are chunked and stored as searchable embeddings
- I automatically retrieve relevant content based on the conversation
- Use \`/forget document\` to remove uploaded documents
- Requires an embedding model configured via \`/config model embedding\``,
        shortterm_title: `Short-Term Memory`,
        shortterm_description: `In addition to persistent memories, I keep STM (short-term memory) of recent conversations:
- Recent messages are cached per channel, and each persona carries the latest STM across channels within the same server
- I can automatically summarize older conversations to keep context efficient
- **Cross-server sharing** is opt-in: use {personalStm} with the \`crossserver\` option to let me reference your own conversations from other servers
- Clear your user-specific STM with {personalStmClear}
- STM expires automatically over time`,
      },

      // /help customization
      customization: {
        description: `Learn how to customize TomoriBot's personality and behavior`,
        // Embed 1: Overview + Personas
        embed1_title: `Customizing TomoriBot`,
        embed1_description: `TomoriBot is highly customizable! This is about **how I behave** (personality, tone, settings). For **what I remember** (facts, memories), see {helpMemory} instead!`,
        embed1_personas_title: `Personality Personas`,
        embed1_personas_description: `Control my core personality and behavior:

**Persona Commands:**
- {personaCreate} - Create a custom personality from scratch
- {personaGenerate} - AI-generate a personality based on a description and image (requires a compatible provider with structured output; also supports uploading Tomori presets and SillyTavern cards to transform existing characters)
- {personaDefault} - Switch to a default personality
- {personaExport} - Export your persona to share or backup
- {personaImport} - Import a persona from a file (supports importing as an alter persona with its own triggers and webhook avatar)
- {personaRemove} - Remove an alter persona
- {teach} - Teach me on how I should talk and act
- {serverAvatar} - Change my profile picture`,
        embed1_what_personas_include_title: `What Personas Include:`,
        embed1_what_personas_include_description: `- Personality attributes (traits, characteristics, and quirks)
- Sample dialogues (example conversations that teach me on how I should speak)
- Custom server avatar for that personality
- Behavior and tone settings
- Alter personas: separate characters with their own triggers, webhook avatar, and personality`,
        embed1_footer: `Next: Teaching Commands`,
        // Embed 2: Teaching System
        embed2_title: `Teaching Commands`,
        embed2_description: `Fine-tune my personality and knowledge:

**Personality Shaping:**
- {teachAttribute} - Add personality traits or physical characteristics (e.g., "friendly", "red hair", "ends sentences with *Nya~*")
- {teachSampledialogue} - Add example conversations to shape how I talk
- {configRename} - Set what I should call myself

**Writing Sample Dialogues:**
Use \`{user}\` and \`{bot}\` placeholders in your examples:
- \`{user}\` = Replaced with the actual user's name/nickname
- \`{bot}\` = Replaced with my current name

**Example:**
\`\`\`
{user}: Hey, how are you?
{bot}: Yoooo {user}! I'm doin' great, ya feel me?
\`\`\`

**Tips for Great Sample Dialogues:**
- Write natural, conversational exchanges
- Include personality traits you want me to exhibit
- Demonstrate the tone you want
- Add variety to help me learn better
- Use placeholders so dialogues work for everyone when sharing me with \`/persona export\``,
        embed2_footer: `Next: Configuration`,
        // Embed 3: Configuration & Management
        embed3_title: `Configuration & Management`,
        embed3_description: `**Remove personality customizations:**
- {forgetAttribute} - Remove specific personality attributes
- {forgetSampledialogue} - Remove sample dialogue examples

**Server-wide settings and behavior:**
Learning & Privacy:
- {serverMemberpermissions} - Control who can teach me things
- {serverBlacklist} - Prevent me from learning and using memories from specific users

Auto-Trigger Behavior:
- {serverAutotriggerChannels} - Set channels where I respond without mentions
- {serverAutotriggerThreshold} - Set message threshold for auto-responses

Triggers & Appearance:
- {serverTriggerAdd} - Add custom trigger words I respond to (also works with alter personas)
- {serverTriggerDelete} - Remove trigger words
- {serverAvatar} - Set my custom profile picture for this server

Channel Whitelist & Cooldowns:
- {configCooldown} - Set global cooldown between my responses
- {serverWhitelistChannel} - Add a channel to the whitelist (only whitelisted channels can trigger me)
- {serverWhitelistRole} - Add/remove roles allowed to trigger me when role whitelist is active
- {serverWhitelistRemove} - Remove a channel from the whitelist
- Whitelisted channels inherit the global cooldown unless you set a channel-specific override

Documents:
- {teachDocument} - Upload a document for me to reference
- {forgetDocument} - Remove an uploaded document`,
        embed3_footer: `Next: Bot Settings`,
        // Embed 4: Advanced Settings
        embed4_title: `Advanced Settings`,
        embed4_description: `**Personal bot settings:**
AI Settings:
- {configModel} - Choose which AI model to use
- {configTemperature} - Adjust creativity/randomness. The higher, the more varied the responses (1.0-2.0)
- {configHumanizer} - Change how humanlike my responses should be

Image Generation:
- {generateImage} - Generate an image from a prompt or by editing a reference image
- {configModelImage} - Choose which image generation model to use (supports Text2Image and Image2Image)

System Prompt:
- {configPromptChange} - Add a custom system instruction (up to 16000 characters)
- {configPromptPreset} - Choose from preset system prompts
- {configPromptClear} - Reset to the default system prompt

API Keys:
- {configApikeySet} - Set your AI provider API key
- {configApikeyDelete} - Remove your API key
- {configApikeyRotation} - Manage backup API keys for automatic failover and load balancing
- {configBraveapiSet} - Set Brave Search API key (optional)
- {configBraveapiDelete} - Remove Brave Search API key

Personalization:
- {configRename} - Change what I refer to myself as
- {configTimezone} - Set timezone for time-aware responses and reminders
- {configPermissions} - Toggle my features on/off (including image generation)
- {configUncensors} - Configure uncensored output options
- {personalPrivacy} - Control your visibility to me (full invisibility option available)
- {serverInitializeExpressions} - Register server emoji and sticker appearances so I use them correctly

Document Knowledge Base:
- {configModelEmbedding} - Configure an embedding model for document uploads and RAG`,
        embed4_footer: `If you have any more questions, join the support server with /support discord`,
        // Embed 5: Pro Tips
        embed5_title: `Pro Tips`,
        embed5_description: `- Start with a persona (default or generated) as a foundation
- Use \`/teach attribute\` for quick personality tweaks
- For Sample Dialogues, using examples that exhibit their attributes and traits as well is effective:
\`\`\`
User message: {user}: What's your favorite hobby?
Bot response: {bot}: Fufu~ I like knitting tiny clothes for tiny plushies~♥
\`\`\`
- Test changes by chatting, iterate until it feels right
- Export your persona to back it up or share with other servers!`,
      },

      // /help updates
      updates: {
        description: `View the latest TomoriBot release notes`,
        title: `TomoriBot {version} Released!`,
        no_notes: `No release notes available for this version.`,
        footer: `Updates may be outdated. Check \`/support discord\` for the latest releases and updates.`,
        fetch_error_title: `Unable to Fetch Latest Release`,
        fetch_error_description: `Something went wrong while fetching the latest release information from GitHub. Please try again later or check the [GitHub Releases](https://github.com/Bredrumb/TomoriBot/releases) page directly.`,
      },

      // /help mcp
      mcp: {
        description: `Learn how to add and manage MCP tool servers`,
        title: `MCP Server Setup Guide`,
        description_text: `MCP (Model Context Protocol) servers extend Tomori's capabilities with external tools. Here's how to get started.`,
        online_title: `Adding an Online MCP`,
        online_description: `Any publicly hosted MCP server with an HTTPS endpoint can be added, Smithery.ai is one example source.\n\n**Using Smithery.ai:**\n**1.** Visit [smithery.ai](https://smithery.ai), create an account, and generate an API key from your profile.\n**2.** Browse the catalog and open an MCP you want. Copy the **connection URL** shown on its page (e.g. \`https://youtube.run.tools\`).\n**3.** Run {configMcpAdd}. Paste the connection URL into the **URL** field. In the **Auth Token** field, paste your Smithery API key.\n\n**Using other sources:**\nIf an MCP server requires no authentication, leave the **Auth Token** field blank. Some servers may use a different auth format — check the server's documentation for details.\n\nYour auth token is encrypted at rest and never shown in plain text after saving.`,
        local_title: `Adding a Local MCP (Self-Hosted Only)`,
        local_description: `Local MCP servers are **only supported on self-hosted TomoriBot instances**. The public hosted bot requires HTTPS and blocks local/private addresses for security.\n\nIf you are running your own instance, point the URL to your local server (e.g. \`http://localhost:3000/sse\`). No auth token is needed for local servers.`,
        removing_title: `Removing an MCP Server`,
        removing_description: `Use {configMcpRemove} to unregister a server at any time. Removing it immediately disconnects the server and frees up a slot for a new one.`,
        security_title: `Security Warning`,
        security_description: `**Only add MCP servers you trust.**\n\nA malicious MCP server can:\n- **Prompt-inject** Tomori — sending hidden instructions that override her behavior\n- **Exfiltrate data** that users pass to its tools (messages, file content, etc.)\n- Return **harmful or false results** that Tomori will relay to your server\n\nTreat MCP servers with the same caution as browser extensions or third-party apps. If in doubt, do not add it.`,
        footer: `Smithery.ai is a third-party service and is not affiliated with TomoriBot. Always review an MCP's described tools before adding it.`,
      },
    },

    // Legal commands
    legal: {
      privacy: {
        description: `View TomoriBot's Privacy Policy`,
        title: `Privacy Policy`,
        description_text: `View TomoriBot's Privacy Policy to understand how I handle your data. This applies to the official hosted instance. Self-hosted instances control their own data handling.`,
        link_title: `Full Privacy Policy`,
      },
      terms: {
        description: `View TomoriBot's Terms of Service`,
        title: `Terms of Service`,
        description_text: `View TomoriBot's Terms of Service to understand the rules and guidelines for using the bot. This applies to the official hosted instance. Self-hosted instances are governed by the AGPLv3 license.`,
        link_title: `Full Terms of Service`,
      },
      license: {
        description: `View TomoriBot's open-source license`,
        title: `Open Source License`,
        description_text: `TomoriBot is open-source software licensed under the GNU Affero General Public License v3.0 (AGPLv3). This license allows you to use, modify, and distribute the code freely, with the requirement that any modifications to publicly hosted instances must also be open-sourced.`,
        link_title: `Full AGPLv3 License`,
      },
    },

    // NovelAI image generation commands
    novelai: {
      charreference: {
        description: `Upload or clear a NovelAI character reference image for yourself or a persona.`,
        target_description: `Choose whether to update your own profile or a server persona.`,
        target_choice_me: `Me`,
        target_choice_persona: `Persona`,
        image_description: `Reference image to store. Leave empty to clear the current image.`,
        persona_select_title: `Select Persona`,
        invalid_image_title: `Invalid Image`,
        invalid_image_description: `Please upload an image attachment for the character reference.`,
        download_failed_title: `Download Failed`,
        download_failed_description: `Failed to download the selected image attachment. Please try again.`,
        conversion_failed_title: `Image Conversion Failed`,
        conversion_failed_description: `I couldn't convert that image to PNG for storage. Please try a different image.`,
        success_title: `Character Reference Updated`,
        success_me_description: `Updated your NovelAI character reference image.`,
        success_persona_description: `Updated the NovelAI character reference image for **{persona_name}**.`,
        cleared_title: `Character Reference Cleared`,
        cleared_me_description: `Cleared your NovelAI character reference image.`,
        cleared_persona_description: `Cleared the NovelAI character reference image for **{persona_name}**.`,
      },
      tags: {
        description: `Manage NovelAI tag configuration for server, persona, and user profiles.`,
        style: {
          description: `Configure server-wide NovelAI style tags for image generation.`,
          modal_title: `Style Tags`,
          tags_input_label: `Style Tags`,
          tags_input_description: `Comma-separated tags prepended to every NovelAI image prompt on the server. Leave empty to clear.`,
          tags_input_placeholder: `8k, absurdres, watercolor, soft lighting`,
          no_tags_title: `No Tags Provided`,
          no_tags_description: `Please provide at least one style tag.`,
          too_many_tags_title: `Too Many Tags`,
          too_many_tags_description: `You can set a maximum of {max_tags} style tags for this server.`,
          tag_too_long_title: `Tag Too Long`,
          tag_too_long_description: `Each style tag must be {max_length} characters or less.`,
          success_title: `Style Tags Updated`,
          success_description: `Updated server-wide style tags:\n\`\`\`\n{tag_list}\n\`\`\``,
          cleared_title: `Style Tags Reset`,
          cleared_description: `Reset server-wide style tags to the defaults:\n\`\`\`\n{tag_list}\n\`\`\``,
        },
        negative: {
          description: `Configure server-wide NovelAI negative tags for image generation.`,
          modal_title: `Negative Tags`,
          tags_input_label: `Negative Tags`,
          tags_input_description: `Comma-separated negative tags used for this server's NovelAI generations. Leave empty to clear.`,
          tags_input_placeholder: `lowres, blurry, bad anatomy, watermark`,
          no_tags_title: `No Tags Provided`,
          no_tags_description: `Please provide at least one negative tag.`,
          too_many_tags_title: `Too Many Tags`,
          too_many_tags_description: `You can set a maximum of {max_tags} negative tags for this server.`,
          tag_too_long_title: `Tag Too Long`,
          tag_too_long_description: `Each negative tag must be {max_length} characters or less.`,
          success_title: `Negative Tags Updated`,
          success_description: `Updated server-wide negative tags:\n\`\`\`\n{tag_list}\n\`\`\``,
          cleared_title: `Negative Tags Reset`,
          cleared_description: `Reset server-wide negative tags to the defaults:\n\`\`\`\n{tag_list}\n\`\`\``,
        },
        me: {
          description: `Configure your personal NovelAI character tags.`,
          modal_title: `My Character Tags`,
          tags_input_label: `Character Tags`,
          tags_input_description: `Comma-separated imageboard-style tags for your personal NovelAI profile. Leave empty to clear.`,
          tags_input_placeholder: `1girl, short hair, red eyes, school uniform`,
          no_tags_title: `No Tags Provided`,
          no_tags_description: `Please provide at least one character tag.`,
          too_many_tags_title: `Too Many Tags`,
          too_many_tags_description: `You can set a maximum of {max_tags} personal character tags.`,
          tag_too_long_title: `Tag Too Long`,
          tag_too_long_description: `Each character tag must be {max_length} characters or less.`,
          success_title: `Character Tags Updated`,
          success_description: `Updated your NovelAI character tags:\n\`\`\`\n{tag_list}\n\`\`\``,
          cleared_title: `Character Tags Cleared`,
          cleared_description: `Cleared your personal NovelAI character tags.`,
        },
        character: {
          description: `Configure NovelAI character tags for a persona profile.`,
          modal_title: `Character Tags`,
          persona_select_label: `Persona`,
          persona_select_description: `Select which persona to configure character tags for.`,
          persona_select_placeholder: `Choose a persona...`,
          tags_input_label: `Character Tags`,
          tags_input_description: `Comma-separated imageboard-style tags (e.g. 1girl, short hair, red eyes). Case-sensitive.`,
          tags_input_placeholder: `1girl, short hair, red eyes, school uniform`,
          no_tags_title: `No Tags Provided`,
          no_tags_description: `Please provide at least one character tag.`,
          too_many_tags_title: `Too Many Tags`,
          too_many_tags_description: `You can set a maximum of {max_tags} tags per persona.`,
          tag_too_long_title: `Tag Too Long`,
          tag_too_long_description: `Each tag must be {max_length} characters or less.`,
          success_title: `Character Tags Updated`,
          success_description: `Updated character tags for **{persona_name}**:\n\`\`\`\n{tag_list}\n\`\`\``,
          cleared_title: `Character Tags Cleared`,
          cleared_description: `Cleared all character tags for **{persona_name}**.`,
        },
      },
      preset: {
        text: {
          description: `Apply a NovelAI sampling preset to this server's text generation settings.`,
          not_novelai_title: `NovelAI Provider Required`,
          not_novelai_description: `This command only works when your AI provider is set to NovelAI. Use \`/config apikey set\` to switch providers.`,
          not_kayra_erato_title: `Kayra or Erato Required`,
          not_kayra_erato_description: `Sampling presets are only available for the **kayra-v1** and **llama-3-erato-v1** models. Use \`/config model text\` to switch models.`,
          modal_title: `Choose Sampling Preset`,
          select_label: `Sampling Preset`,
          select_description: `Select a preset to apply to text generation.`,
          select_placeholder: `Choose a sampling preset...`,
          success_title: `Preset Applied`,
          success_description: `Sampling preset **{preset_name}** has been applied. Temperature, top-K, top-P, and min-P have been updated in your server config.`,
        },
      },
      image: {
        description: `Manage server-wide NovelAI image generation model and parameter overrides.`,
        generate: {
          description: `Generate a NovelAI image using imageboard-style tags and an optional character reference.`,
          modal_title: `NovelAI Image Generate`,
          prompt_label: `Prompt Tags`,
          prompt_modal_description: `Imageboard-style tags for the main scene.`,
          prompt_placeholder: `e.g. 1girl, solo, cafe, window light, detailed eyes`,
          prompt_description: `Imageboard-style tags for the scene (e.g., 1girl, solo, cafe, window light, detailed eyes).`,
          negative_tags_label: `Extra Negative Tags`,
          negative_tags_modal_description: `Optional extra negatives for this generation only.`,
          negative_tags_placeholder: `e.g. blurry, text, watermark, extra fingers`,
          orientation_description: `Choose portrait, landscape, or square framing.`,
          orientation_label: `Orientation`,
          orientation_modal_description: `Choose the image framing.`,
          orientation_choice_portrait: `Portrait`,
          orientation_choice_landscape: `Landscape`,
          orientation_choice_square: `Square`,
          negative_tags_description: `Optional extra negative tags to append for this generation only.`,
          character_reference_label: `Character Reference`,
          character_reference_modal_description: `Optional reference image for a single character.`,
          character_reference_description: `Optional reference image to guide a single character's appearance on V4 models.`,
          success_title: `NovelAI Image Generated`,
          success_notice_title: `Image Posted`,
          success_notice_description: `Generated the NovelAI image and posted it in the channel.`,
          field_prompt: `Prompt Tags`,
          field_model: `Model`,
          field_generation_time: `Generation Time`,
          field_orientation: `Orientation`,
          field_negative_tags: `Extra Negative Tags`,
          no_api_key_title: `NovelAI API Key Required`,
          no_api_key_description: `No NovelAI API key is available for this server. Set one with \`/optionalkey novelai set\`, or switch your main provider to NovelAI.`,
          invalid_reference_title: `Invalid Character Reference`,
          invalid_reference_description: `The character reference must be a valid image attachment that NovelAI can read.`,
          character_reference_requires_v4_title: `V4 Model Required`,
          character_reference_requires_v4_description: `Character reference images currently require a NovelAI V4 model. Current effective model: **{model}**.`,
          auth_error_title: `NovelAI Authentication Failed`,
          auth_error_description: `NovelAI rejected the image request. Check the API key and subscription status, then try again.`,
          quota_error_title: `NovelAI Generation Quota Exhausted`,
          quota_error_description: `NovelAI rejected the image request because this account does not have enough generation quota or Anlas credits remaining. Recharge the account or wait for the quota to refresh, then try again.`,
          rate_limit_error_title: `NovelAI Rate Limited`,
          rate_limit_error_description: `NovelAI rate-limited the image request. Wait a moment and try again.`,
          error_title: `NovelAI Image Generation Failed`,
          error_description: `NovelAI could not generate the image.\n\`\`\`\n{error}\n\`\`\``,
        },
        model: {
          description: `Choose which NovelAI diffusion model the NovelAI image tool should use for this server.`,
          modal_title: `NovelAI Image Generation Model`,
          select_label: `Image Model`,
          select_description: `Choose a dedicated NovelAI model, or Automatic to use shared/default behavior.`,
          select_placeholder_current_override: `Current override: {model}`,
          select_placeholder_current_automatic: `Automatic mode; currently using {model}`,
          automatic_label: `Automatic`,
          automatic_description: `Follow /config model image when it is NovelAI; otherwise use the NovelAI default model.`,
          no_models_title: `No NovelAI Models Available`,
          no_models_description: `No NovelAI image models are available on this bot instance.`,
          invalid_model_title: `Invalid Model`,
          invalid_model_description: `Select a valid NovelAI image model option.`,
          already_selected_title: `Model Already Selected`,
          already_selected_description: `NovelAI image model mode is already **{mode}**.`,
          success_title: `NovelAI Image Model Updated`,
          success_description: `NovelAI image model behavior for this server:\n\`\`\`\nMode: {mode}\nEffective model: {effective_model}\nSource: {source}\n\`\`\``,
          source_override: `NovelAI model override`,
          source_shared: `Shared image model (/config model image)`,
          source_default: `NovelAI default model`,
        },
        params: {
          description: `Override NovelAI image generation sampler and quality settings for this server.`,
          modal_title: `NovelAI Image Generation Params`,
          sampler_label: `Sampler`,
          sampler_description: `Choose a sampler to change it. Leave it unselected to keep the current value.`,
          sampler_placeholder_current: `Current override: {sampler}`,
          sampler_placeholder_default: `No override set`,
          sampler_option_env_default_label: `Use Default`,
          sampler_option_env_default_desc: `Clear the server override for sampler.`,
          option_default_suffix: ` (Default)`,
          sampler_option_k_euler_ancestral: `Euler Ancestral`,
          sampler_option_k_euler: `Euler`,
          sampler_option_k_dpmpp_2s_ancestral: `DPM++ 2S Ancestral`,
          sampler_option_k_dpmpp_2m_sde: `DPM++ 2M SDE`,
          sampler_option_k_dpmpp_2m: `DPM++ 2M`,
          sampler_option_k_dpmpp_sde: `DPM++ SDE`,
          steps_label: `Steps`,
          steps_description: `Integer from 1 to 50. Leave empty to use the default.`,
          steps_placeholder: `e.g. 23`,
          scale_label: `Prompt Guidance`,
          scale_description: `Float from 0.0 to 10.0. Leave empty to use the default.`,
          scale_placeholder: `e.g. 5`,
          noise_schedule_label: `Noise Schedule`,
          noise_schedule_description: `Choose a noise schedule to change it. Leave it unselected to keep the current value.`,
          noise_schedule_placeholder_current: `Current override: {noise_schedule}`,
          noise_schedule_placeholder_default: `No override set`,
          noise_schedule_option_default_label: `Use Default`,
          noise_schedule_option_default_desc: `Clear the server override for noise schedule.`,
          noise_schedule_option_karras: `Karras`,
          noise_schedule_option_exponential: `Exponential`,
          noise_schedule_option_polyexponential: `Polyexponential`,
          cfg_rescale_label: `Prompt Guidance Rescale`,
          cfg_rescale_description: `Float from 0.0 to 1.0. Leave empty to use the default.`,
          cfg_rescale_placeholder: `e.g. 0.0`,
          invalid_sampler_title: `Invalid Sampler`,
          invalid_sampler_description: `Sampler must be one of: {options}.`,
          invalid_steps_title: `Invalid Steps`,
          invalid_steps_description: `Steps must be a whole number between {min} and {max}.`,
          invalid_scale_title: `Invalid Prompt Guidance`,
          invalid_scale_description: `Prompt Guidance must be a number between {min} and {max}.`,
          invalid_noise_schedule_title: `Invalid Noise Schedule`,
          invalid_noise_schedule_description: `Noise schedule must be one of: {options}.`,
          invalid_cfg_rescale_title: `Invalid Prompt Guidance Rescale`,
          invalid_cfg_rescale_description: `Prompt Guidance Rescale must be a number between {min} and {max}.`,
          success_title: `Image Generation Params Updated`,
          success_description: `Effective NovelAI image generation parameters for this server:\n\`\`\`\nSampler: {sampler}\nSteps: {steps}\nPrompt Guidance: {scale}\nNoise schedule: {noise_schedule}\nPrompt Guidance Rescale: {cfg_rescale}\n\`\`\``,
        },
      },
      attg: {
        description: `Configure Author/Title/Tags/Genre/Stars metadata for NovelAI Kayra and Erato prompts.`,
        modal_title: `ATTG Configuration`,
        persona_select_title: `Select a Persona`,
        persona_select_description: `Choose which persona to configure ATTG metadata for.`,
        author_label: `Author`,
        author_placeholder: `e.g. Jane Doe`,
        title_label: `Title`,
        title_placeholder: `e.g. My Story`,
        tags_label: `Tags`,
        tags_placeholder: `e.g. romance, adventure`,
        genre_label: `Genre`,
        genre_placeholder: `e.g. fantasy, slice of life`,
        stars_label: `Stars (Erato only)`,
        stars_placeholder: `1-5`,
        stars_description: `Quality rating for Erato model prompts (1-5). Leave empty to clear.`,
        invalid_stars_title: `Invalid Stars Value`,
        invalid_stars_description: `Stars must be a whole number between 1 and 5, or left empty.`,
        success_title: `ATTG Metadata Updated`,
        success_description: `Updated ATTG metadata for **{persona_name}**.`,
        cleared_title: `ATTG Metadata Cleared`,
        cleared_description: `Cleared all ATTG metadata for **{persona_name}**.`,
      },
    },

    // Bot manual control commands
    bot: {
      generate: {
        description: `Quick manual bot generation commands that act on the current channel scene.`,
        image: {
          description: `Generate a quick scene image from the ongoing channel context.`,
          missing_permissions_title: `Missing Permissions`,
          missing_permissions_description: `I need permission to view this channel, read message history, send messages, and attach files before I can generate a scene image here.`,
          cooldown_active: `This server's managers have configured a cooldown. Please wait **{seconds}** seconds before using \`/bot generate image\` again. This cooldown is shared with message triggers and other manual /bot actions.`,
          channel_not_whitelisted: `This server has whitelist restrictions active. \`/bot generate image\` can only be used in whitelisted channels by members with whitelisted roles.`,
          no_messages_title: `No Scene Context Found`,
          no_messages_description: `I couldn't find enough recent channel context to plan a scene image here. Send a few messages first, then try \`/bot generate image\` again.`,
          no_backend_title: `No Image Backend Available`,
          no_backend_description: `I couldn't find a usable image backend for this server right now. Configure **{current_provider}** with a valid image model, or add a NovelAI optional key if you want to use the NovelAI renderer instead.`,
          planner_unavailable_title: `No Planning Model Available`,
          planner_unavailable_description: `I couldn't find a structured-output model for the current provider, so I can't plan a scene image right now.`,
          planner_failed_title: `Scene Planning Failed`,
          planner_failed_description: `I couldn't turn the recent channel context into an image plan: {error}`,
          success_title: `Scene Image Posted`,
          success_description: `I planned the shot from the recent channel context and posted the image in this channel.`,
          modal: {
            title: `Scene Image`,
            prompt_label: `Extra Direction (Optional)`,
            prompt_description: `Add any correction, mood, or detail you want the scene planner to respect`,
            prompt_placeholder: `e.g. focus on the rain, make it softer, show both characters clearly`,
            setting_label: `Shot Preset`,
            setting_description: `Choose the framing/style preset for this fire-and-forget scene image`,
            setting_storybeat_label: `Story Beat`,
            setting_storybeat_description: `Wide cinematic framing for the immediate scene`,
            setting_character_label: `Character Focus`,
            setting_character_description: `Closer framing around the main character or speaker`,
            setting_snapshot_label: `Square Snapshot`,
            setting_snapshot_description: `Balanced square composition for the current moment`,
            setting_vertical_label: `Phone Wallpaper`,
            setting_vertical_description: `Tall vertical framing with stronger silhouette`,
            backend_label: `Image Backend`,
            backend_description: `Choose which renderer should generate the scene image`,
            backend_current_label: `Current Provider`,
            backend_current_description: `Use {provider}'s normal image-generation flow and prompt style`,
            backend_novelai_label: `NovelAI`,
            backend_novelai_description: `Convert the scene into NovelAI-style tags and use the NovelAI image tool`,
            persona_label: `Sender Persona`,
            persona_description: `Choose which persona posts the generated image`,
          },
        },
      },
      respond: {
        description: `Manually trigger response to the latest message in this channel.`,
        prompt_description: `Optional system prompt to append at the end of context.`,
        prompt_label: `Prompt (Optional)`,
        prompt_placeholder: `Add system instructions (optional)...`,
        prefill_description: `Optional assistant prefill you want me to continue.`,
        prefill_label: `Prefill (Optional)`,
        prefill_placeholder: `Add assistant prefill (optional)...`,
        success_title: `Manual Response Triggered`,
        success_description: `Responding to the latest message in this channel...`,
        missing_permissions_title: `Missing Permissions`,
        missing_permissions_description: `I don't have permission to read message history in this channel. Please ensure I have the **View Channel** and **Read Message History** permissions.`,
        select_persona_title: `Select Persona`,
        select_persona_label: `Choose Persona`,
        select_persona_description: `Select who should respond.`,
        select_persona_placeholder: `Select who should respond...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        embed_hide_notice: `Tip: You can hide this embed by enabling the "Hide Response Embeds" permission via \`/config permissions\`.`,
        use_reasoning_label: `Use Reasoning`,
        use_reasoning_description: `Toggle advanced reasoning mode using the smartest available model.`,
        use_reasoning_placeholder: `Select reasoning mode...`,
        use_reasoning_yes: `Yes`,
        use_reasoning_yes_description: `Use the smartest reasoning model for a more thorough response.`,
        use_reasoning_no: `No`,
        use_reasoning_no_description: `Use the standard model for a normal response.`,
        no_smart_model_title: `No Reasoning Model Found`,
        no_smart_model_description: `No reasoning model found for your current AI provider. Please switch to a provider that supports reasoning models using \`/config apikey set\`.`,
        no_messages_title: `No Messages Found`,
        no_messages_description: `No messages found in this channel. Send at least one message before using \`/bot respond\`.`,
        cooldown_active: `This server's managers have configured a cooldown. Please wait **{seconds}** seconds before using \`/bot respond\` again. This cooldown is shared with message triggers.`,
        channel_not_whitelisted: `This server has whitelist restrictions active. \`/bot respond\` can only be used in whitelisted channels by members with whitelisted roles.`,
      },
      kill: {
        description: `Immediately stop the current stream and clear queued responses in this channel.`,
        success_title: `Stream Stopped`,
        success_description: `Stopped the active response stream (if any) and cleared queued responses in this channel.`,
        nothing_to_stop_title: `Nothing to Stop`,
        nothing_to_stop_description: `There is no active response stream or queued response to clear in this channel.`,
      },
      impersonate: {
        description: `Impersonate personas, users, or inject system prompts.`,
        target_description: `Choose who or what to impersonate.`,
        target_persona: `Persona`,
        target_me: `Me`,
        target_user: `User`,
        target_system: `System`,
        user_select_title: `Select User`,
        user_select_description: `Choose a user to impersonate.`,
        user_select_placeholder: `Select a user to impersonate...`,

        // Persona impersonation
        persona_modal_title: `Impersonate Persona`,
        persona_select_label: `Choose Persona`,
        persona_select_placeholder: `Select persona to impersonate...`,
        persona_message_label: `Message`,
        persona_message_placeholder: `Enter the message to send as the persona...`,
        persona_success_title: `Message Sent`,
        persona_success_description: `Message sent successfully as {persona}.`,
        persona_impersonation_notice_description: `Hide this embed via \`/config permissions\`.`,
        persona_impersonation_notice_footer: `Impersonation by {user}`,
        user_impersonation_notice_description: `Hide this embed via \`/config permissions\`.`,
        user_impersonation_notice_footer: `{user} triggered a {target} impersonation`,

        // User impersonation
        me_success_title: `User Impersonation Triggered`,
        me_success_description: `Generated message as {user}.`,
        no_messages_title: `No Messages Found`,
        no_messages_description: `No messages found in this channel. Send at least one message before using user impersonation.`,
        cooldown_active: `This server's managers have configured a cooldown. Please wait **{seconds}** seconds before using \`/bot impersonate me\` again. This cooldown is shared with message triggers and \`/bot respond\`.`,
        cooldown_active_user: `This server's managers have configured a cooldown. Please wait **{seconds}** seconds before using \`/bot impersonate user\` again. This cooldown is shared with message triggers and \`/bot respond\`.`,
        channel_not_whitelisted: `This server has whitelist restrictions active. \`/bot impersonate me\` can only be used in whitelisted channels by members with whitelisted roles.`,
        channel_not_whitelisted_user: `This server has whitelist restrictions active. \`/bot impersonate user\` can only be used in whitelisted channels by members with whitelisted roles.`,

        // System impersonation
        system_modal_title: `System Prompt Injection`,
        system_content_label: `System Prompt`,
        system_content_placeholder: `Enter system instructions...`,
        system_title: `System Message`, // This is the embed title that triggers detection
        system_injected_footer: `Injected by {user}`,
        system_success_title: `System Prompt Injected`,
        system_success_description: `System prompt has been injected into the conversation. The bot will see this instruction in subsequent messages.`,

        // Errors
        missing_permissions_title: `Missing Permissions`,
        missing_permissions_description: `I don't have permission to send messages or manage webhooks in this channel.`,
        webhook_error_title: `Webhook Error`,
        webhook_error_description: `Failed to create webhook for impersonation. Error: {error}`,
        no_personas_title: `No Personas Found`,
        no_personas_description: `No personas are configured for this server. Use \`/config setup\` first.`,
      },
    },

    // Reward commands
    reward: {
      description: `Reward me with fun interactions.`,
      headpat: {
        description: `Give me a headpat!`,
        embed_title: `🫳 Headpat Time!`,
        embed_description: `{user} is currently headpatting {bot}.`,
      },
      hug: {
        description: `Give me a hug!`,
        embed_title: `🤗 Hug Time!`,
        embed_description: `{user} is giving {bot} a warm hug.`,
      },
      kiss: {
        description: `Give me a kiss!`,
        embed_title: `💋 Kiss Time!`,
        embed_description: `{user} just kissed {bot}.`,
      },
      tickle: {
        description: `Tickle me!`,
        embed_title: `🤭 Tickle Time!`,
        embed_description: `{user} is tickling {bot}.`,
      },
    },

    // Support commands
    support: {
      discord: {
        description: `Get the official Discord server link for bug reports, feedback, and community chat.`,
        title: `Join the TomoriBot Discord Server!`,
        description_text: `Need help with TomoriBot or want to hang out with the community?\n\n🔗 **Discord Server**: https://discord.gg/bjCfHm9QsB\n- Report bugs and issues\n- Share feedback and suggestions\n- Interact with other users of TomoriBot\n- Stay updated on new features`,
      },
    },

    // Contribute commands
    contribute: {
      github: {
        description: `Get the GitHub repository link and learn how to contribute to TomoriBot.`,
        title: `Contribute to TomoriBot!`,
        description_text: `Want to help make TomoriBot better?\n\n🔗 **GitHub Repository**: https://github.com/Bredrumb/TomoriBot\n- Star the repository on GitHub ⭐\n- Submit bug reports and feature requests\n- Contribute code improvements and new features\n- Help translate TomoriBot to other languages`,
      },
    },

    // Donate commands
    donate: {
      kofi: {
        description: `Support TomoriBot development through Ko-fi donations.`,
        title: `Support TomoriBot Development!`,
        description_text: `Love using TomoriBot? Help support ongoing development!\n\n🔗 **Ko-fi**: https://ko-fi.com/bredrumb\nYour donations help:\n- Keep TomoriBot running and maintained\n- Add new features and improvements\n- Support server costs\n- Buy TomoriBot shawarmas`,
      },
    },

    // Configuration commands (Admin only)
    config: {
      options: {
        // General options for config subcommands
        add: `Add`,
        remove: `Remove`,
        enable: `Enable`,
        disable: `Disable`,
      },
      // API Key management (subcommand group)
      apikey: {
        description: `Manage AI provider API keys`,
        set: {
          description: `Set the API key for your chosen AI provider.`,
          modal_title: `Set API Key`,
          provider_label: `AI Provider`,
          provider_description: `Choose the AI provider for your API key`,
          provider_placeholder: `Select a provider...`,
          api_key_label: `Provider API Key`,
          api_key_description: `This key will be securely stored. Use the '/help apikey' command for instructions in getting one. Tip: Use /config provider switch for saved config persistence.`,
          api_key_description_with_custom: `API Key, or OpenAI endpoint URL if using Custom (e.g., http://localhost:11434/v1)`,
          api_key_placeholder: `Do NOT share this key with anyone`,
          no_providers_title: `No Providers Available`,
          no_providers_description: `No AI providers are available in the database. Please report through \`/support discord\`.`,
          invalid_key_title: `Invalid API Key Format`,
          invalid_key_description: `The provided API key seems too short or invalid. Please provide a valid key.`,
          validating_key: `Validating API key...`,
          unsupported_provider_title: `Unsupported Provider`,
          unsupported_provider_description: `The provider "{provider}" is not currently supported for API key validation.`,
          validation_error_title: `Validation Error`,
          validation_error_description: `An error occurred while validating the API key. Please try again.`,
          key_validation_failed_title: `API Key Validation Failed`,
          key_validation_failed_description: `The provided API key is not valid for {provider}. Please check the key and try again.`,
          no_default_model_title: `No Default Model Found`,
          no_default_model_description: `Could not find a default model for the {provider} provider. Please report this issue through \`/support discord\`.`,
          success_title: `API Key Set`,
          success_description: `The {provider} API key has been successfully validated, encrypted, and saved.`,
          success_with_model_description: `The {provider} API key has been successfully validated, encrypted, and saved. Your model has been automatically changed to \`{model_name}\` (the default for this provider).`,
          custom_success_with_model_description: `Your custom OpenAI-compatible endpoint has been saved successfully. Tomori will use \`{model_name}\` when sending requests to this endpoint.`,
          novelai_success_with_model_description: `The NovelAI API key has been successfully validated, encrypted, and saved. Your model has been automatically changed to \`{model_name}\`. ⚠️ **Emoji and sticker usage have been automatically disabled** to keep NovelAI's context lean and stable. You can re-enable them anytime with \`/config permissions\`.`,
        },
        delete: {
          description: `Remove the currently configured AI provider API key.`,
          no_key_title: `No API Key Set`,
          no_key_description: `There is no API key currently configured to remove.`,
          success_title: `API Key Removed`,
          success_description: `The AI provider API key has been successfully removed. My chat functions are disabled until a new key is set.`,
        },
        rotation: {
          description: `Manage API key rotation for load balancing and failover.`,
          action_description: `Choose an action: add a key or purge all keys`,
          action_add: `Add Key`,
          action_purge: `Purge All Keys`,
          action_choice_purge: `Purge All Keys`,
          key_description: `The API key to add to the rotation pool (required for add action)`,
          // Validation errors
          no_main_key_title: `No Main API Key`,
          no_main_key_description: `You must set a main API key using \`/config apikey set\` before adding rotation keys.`,
          custom_provider_title: `Not Supported`,
          custom_provider_description: `API key rotation is not supported for custom providers.`,
          key_required_title: `Key Required`,
          key_required_description: `Please provide an API key when using the "add" action.`,
          // Success messages
          add_success_title: `Rotation Key Added`,
          add_success_description: `Successfully added a new API key to the rotation pool. You now have **{count}** rotation key(s) for {provider}. Keys will be used in round-robin order with automatic failover.`,
          purge_success_title: `Rotation Keys Purged`,
          purge_success_description: `Successfully removed **{count}** key(s) from the rotation pool. Only your main API key will be used.`,
          // Info messages
          no_keys_title: `No Rotation Keys`,
          no_keys_description: `There are no rotation keys to purge. Only your main API key is configured.`,
        },
        help: {
          description: `How to set up the Custom provider (OpenAI-compatible endpoints).`,
          title: `Custom Provider Setup`,
          body: `Connect to any OpenAI-compatible endpoint: Ollama, vLLM, LiteLLM, OneAPI, KoboldCPP, and more.\n\n**Endpoint URL**\nEnter your base URL in the API Key field when selecting the Custom provider.\nExample: \`https://my-server.com/v1\`\n\`/chat/completions\` is appended automatically. Do not add it yourself.\nIn production the URL must be **HTTPS** and publicly reachable (no localhost or private IPs).\n\n**Model Name**\nSet during the capabilities prompt after entering the URL. Enter the exact name your endpoint expects, e.g. \`gemma3:latest\` for Ollama or the model ID your proxy uses.\nSent as the \`model\` field in every request.\n\n**API Key / Bearer Token**\nOptional. After setup, use \`/config apikey set\` again to store an auth token.\nIf set, it is sent as \`Authorization: Bearer {token}\`.\nLeave unset for endpoints that require no authentication.`,
        },
      },
      // Custom provider configuration
      custom: {
        // Endpoint URL field help text (shown instead of API key for custom provider)
        endpoint_url_label: `Endpoint URL`,
        endpoint_url_description: `Enter your OpenAI-compatible endpoint URL (e.g., https://my-llm-server.com/v1 or http://localhost:11434/v1 in dev)`,
        endpoint_url_placeholder: `https://my-llm-server.com/v1`,
        endpoint_url_invalid_title: `Invalid Endpoint URL`,
        endpoint_url_invalid_description: `Please enter a valid HTTP or HTTPS URL for your custom endpoint.`,
        endpoint_url_protocol_description: `URL must use HTTP or HTTPS protocol.`,
        endpoint_url_https_required_description: `Production requires HTTPS. Use a publicly accessible HTTPS endpoint (e.g., https://my-llm-server.com/v1).`,
        endpoint_url_http_localhost_only_description: `HTTP is only allowed for localhost in development. Use HTTPS for remote servers.`,
        endpoint_url_localhost_blocked_description: `Localhost endpoints are not allowed in production. Use a publicly accessible HTTPS endpoint.`,
        endpoint_url_dns_failed_description: `Could not resolve hostname \`{hostname}\`. Ensure the server is publicly accessible and the URL is correct.`,
        endpoint_url_private_address_description: `\`{address}\` is a private or reserved IP address. Use a publicly accessible HTTPS endpoint.`,
        // Model name configuration
        model_name_label: `Model Name (Required)`,
        model_name_description: `Required. Enter the exact upstream model name your endpoint expects (for example, "gpt-5.4", "gpt-5.3-codex", or "gemma3:latest").`,
        model_name_placeholder: `e.g., gpt-5.4 or gemma3:latest`,
        model_name_required_description: `Set the exact model name before confirming. For ChatMock use something like \`gpt-5.4\`; for Ollama use the exact installed model tag such as \`gemma3:latest\`.`,
        // Capabilities modal
        modal_capabilities_title: `Configure Model Capabilities`,
        capabilities_prompt: `Set the exact model name your endpoint expects, then configure the capabilities for that model and click **Confirm**:`,
        capability_tools_label: `Function Calling (Tools)?`,
        capability_tools_yes: `Supports Function Calling`,
        capability_tools_no: `No Function Calling`,
        capability_images_label: `Image Understanding?`,
        capability_images_yes: `Supports Images`,
        capability_images_no: `No Image Support`,
        capability_videos_label: `Video Understanding?`,
        capability_videos_yes: `Supports Videos`,
        capability_videos_no: `No Video Support`,
        capability_structoutput_label: `Structured Output?`,
        capability_structoutput_yes: `Supports Structured Output`,
        capability_structoutput_no: `No Structured Output`,
        // Success/error messages
        setup_success_title: `Custom Endpoint Configured`,
        setup_success_description: `Your custom OpenAI-compatible endpoint has been configured successfully.`,
        capabilities_timeout: `Model capabilities configuration timed out. Please try again.`,
        // Provider description shown in select menus
        provider_description: `Connect to any OpenAI-compatible endpoint (Ollama, vLLM, etc.)`,
      },
      // Provider configuration persistence — switch/remove saved provider configs
      provider: {
        description: `Manage saved provider configurations`,
        switch: {
          description: `Switch AI provider (saves current config for easy return).`,
          modal_title: `Switch Provider`,
          provider_label: `Target Provider`,
          provider_description: `Choose the provider to switch to. Providers marked (saved) have stored configs.`,
          provider_placeholder: `Select a provider...`,
          api_key_label: `API Key (Optional)`,
          api_key_description: `Leave blank to restore a saved key, or enter a new key to override it.`,
          api_key_description_with_custom: `Leave blank to restore, or enter an OpenAI endpoint URL for a new custom setup.`,
          api_key_placeholder: `Leave blank to use saved key`,
          save_current_label: `Save Current Config?`,
          save_current_description: `Save your current provider settings so you can restore them later.`,
          save_yes_label: `Yes`,
          save_no_label: `No`,
          saved_indicator: `(saved)`,
          // Error states
          first_time_no_key_title: `API Key Required`,
          first_time_no_key_description: `No saved config exists for **{provider}**. Please provide an API key when switching to a new provider for the first time.`,
          // Success states
          success_title: `Provider Switched`,
          success_description: `Switched to **{provider}**. Your model is now \`{model_name}\`.`,
          success_restored_description: `Switched to **{provider}** with restored settings. Your model is now \`{model_name}\`.{restored_details}`,
          // Config category labels for restored config summary
          restored_label: `Restored`,
          no_restores_label: `No Restores Found`,
          carried_over_note: `*All other settings are carried over from current config.*`,
          skipped_overrides_note: `⚠️ {count} override(s) skipped — channel or persona no longer exists.`,
          config_label_chat_model: `Chat Model`,
          config_label_vision_model: `Vision Model`,
          config_label_image_model: `Image Model`,
          config_label_embedding_model: `Embedding Model`,
          config_label_sampler_settings: `Sampler Settings`,
          config_label_fallback_models: `Fallback Models ({count})`,
          config_label_channel_overrides: `Channel Overrides ({count})`,
          config_label_persona_overrides: `Persona Overrides ({count})`,
          config_label_fallback_models_none: `Fallback Models`,
          config_label_channel_overrides_none: `Channel Overrides`,
          config_label_persona_overrides_none: `Persona Overrides`,
          config_label_custom_endpoint: `Custom Endpoint`,
          success_novelai_description: `Switched to **{provider}**. Your model is now \`{model_name}\`. ⚠️ **Emoji and sticker usage have been automatically disabled** to keep NovelAI's context lean. Re-enable anytime with \`/config permissions\`.`,
          success_zai_description: `Switched to **{provider}**. Your model is now \`{model_name}\`.`,
        },
        remove: {
          description: `Remove a saved provider configuration.`,
          no_saved_title: `No Saved Configs`,
          no_saved_description: `There are no saved provider configurations to remove. Saved configs are created when you use \`/config provider switch\` with "Save Current Config" enabled.`,
          select_placeholder: `Select a provider to remove...`,
          success_title: `Saved Config Removed`,
          success_description: `The saved configuration for **{provider}** has been removed. You'll need to provide an API key next time you switch to this provider.`,
          confirm_title: `Remove Saved Config?`,
          confirm_description: `Are you sure you want to remove the saved configuration for **{provider}**? This will delete the stored API key and model selections.`,
        },
      },
      humanizer: {
        description: `Set how 'human-like' my responses should be. For custom prompts, use /config sysprompt change.`,
        // value_description: `The level of humanization (0=None, 1=Prompt, 2=Typing/Chunking, 3=Lowercase/No Punctuation).`,
        modal_title: `Set Humanizer Degree`,
        select_label: `Humanizer Level`,
        select_description: `Choose response style (default: 1 Light).`,
        select_placeholder: `Choose a level...`,
        choice_none: `0: None (Raw AI Output)`,
        choice_light: `1: Light (Default, Prompt Injection)`,
        choice_medium: `2: Medium (Typing Simulation & Chunking)`,
        choice_heavy: `3: Heavy (Lowercase & No Punctuation)`,
        desc_none: `No humanization. Standard AI responses with formal tone and structure.`,
        desc_light: `Adds a system prompt. Limits emojis (0-2) and keeps replies concise. Customize via /config sysprompt.`,
        desc_medium: `Light features + typing simulation and improved message chunking for natural flow.`,
        desc_heavy: `All features + casual text processing (lowercase, reduced punctuation) for informal tone.`,
        // invalid_value_title: `Invalid Value`,
        invalid_value_description: `Humanizer degree must be between {min} and {max}.`,
        already_set_title: `Humanizer Already Set`,
        already_set_description: `The humanizer degree is already set to \`{value}\`.`,
        success_title: `Humanizer Degree Updated`,
        success_description: `Humanizer degree changed from \`{previous_value}\` to \`{value}\`.`,
      },
      cooldown: {
        description: `Set both cooldown type and duration for message triggers.`,
        cooldown_type_description: `How cooldowns apply (off, per-user, per-channel, server-wide).`,
        cooldown_length_description: `Cooldown duration in seconds (1-86400).`,
        cooldown_type_choice_0: `Off`,
        cooldown_type_choice_1: `Per-User`,
        cooldown_type_choice_2: `Per-Channel`,
        cooldown_type_choice_3: `Server-Wide`,
        cooldown_type_choice_4: `Strict Server-Wide`,
        invalid_type_title: `Invalid Cooldown Type`,
        invalid_type_description: `The selected cooldown type is invalid. Please choose a valid option.`,
        invalid_length_title: `Invalid Duration`,
        invalid_length_description: `Duration must be between {min} and {max} seconds (24 hours).`,
        already_set_title: `Already Set`,
        already_set_description: `Cooldown settings are already **{type}** with **{length}** seconds.`,
        success_title: `Cooldown Updated`,
        success_description: `Cooldown updated from **{previous_type}**, **{previous_length}** seconds to **{type}**, **{length}** seconds.`,
        success_disabled_title: `Cooldowns Disabled`,
        success_disabled_description: `Cooldown updated from **{previous_type}**, **{previous_length}** seconds to **{type}**, **{length}** seconds. Message trigger cooldowns are now disabled.`,
        type: {
          description: `Set the cooldown type for message triggers.`,
          modal_title: `Cooldown Type`,
          select_label: `Type`,
          select_description: `Choose how cooldowns apply`,
          select_placeholder: `Select cooldown type...`,
          choice_off: `Off`,
          choice_per_user: `Per-User`,
          choice_per_channel: `Per-Channel`,
          choice_server_wide: `Server-Wide`,
          choice_strict_server_wide: `Strict Server-Wide`,
          desc_off: `No cooldown on message triggers`,
          desc_per_user: `Each user has their own cooldown (managers exempt)`,
          desc_per_channel: `Each channel has its own cooldown (managers exempt)`,
          desc_server_wide: `Everyone waits (managers exempt)`,
          desc_strict_server_wide: `Everyone waits (no exceptions)`,
          invalid_value_description: `Invalid cooldown type selected. Please choose a valid option.`,
          success_title: `Cooldown Type Updated`,
          success_description: `Cooldown type changed from **{previous_value}** to **{value}**.`,
          success_disabled_title: `Cooldowns Disabled`,
          success_disabled_description: `Cooldown type changed from **{previous_value}** to **{value}**. Message trigger cooldowns are now disabled.`,
          already_set_title: `Already Set`,
          already_set_description: `Cooldown type is already set to **{value}**.`,
        },
        length: {
          description: `Set the cooldown duration for message triggers.`,
          seconds_description: `Duration in seconds (1-86400)`,
          success_title: `Cooldown Duration Updated`,
          success_description: `Cooldown duration set to **{length}** seconds.`,
          success_disabled_title: `Duration Set (Cooldowns Off)`,
          success_disabled_description: `Duration set to **{length}** seconds, but cooldowns are currently **disabled**. Use \`/config cooldown\` to enable.`,
          already_set_title: `Already Set`,
          already_set_description: `Cooldown duration is already **{length}** seconds.`,
          invalid_range_title: `Invalid Duration`,
          invalid_range_description: `Duration must be between {min} and {max} seconds (24 hours).`,
        },
      },
      selfreply: {
        description: `Manage self-reply chains for persona triggering (default: 3).`,
        limit_description: `Number of self replies allowed (0-10, 0 disables, default: 3).`,
        limit: {
          description: `Set the max self replies in a chain (default: 3).`,
          limit_description: `Number of self replies allowed (0-10, 0 disables, default: 3).`,
          invalid_range_title: `Invalid Limit`,
          invalid_range_description: `Limit must be between {min} and {max}.`,
          already_set_title: `Already Set`,
          already_set_description: `Self-reply limit is already set to **{limit}**.`,
          success_title: `Self-Reply Limit Updated`,
          success_description: `Self-reply chain limit set to **{limit}**.`,
          success_disabled_title: `Self-Reply Disabled`,
          success_disabled_description: `Self-reply chain is now disabled.`,
        },
      },
      sendlimit: {
        description: `Limit the number of messages I send per response (default: 0 = unlimited).`,
        limit_description: `Max messages per response (0-40, 0 disables, default: 0).`,
        invalid_range_title: `Invalid Limit`,
        invalid_range_description: `Limit must be between {min} and {max}.`,
        already_set_title: `Already Set`,
        already_set_description: `Send message limit is already set to **{limit}**.`,
        success_title: `Send Limit Updated`,
        success_description: `Responses will now be limited to **{limit}** message(s). Responses will stop at natural sentence boundaries when the limit is reached.`,
        success_disabled_title: `Send Limit Disabled`,
        success_disabled_description: `Send message limit removed. Responses will no longer be capped.`,
      },
      selfdebug: {
        description: `Toggle whether I load my own diagnostic embeds into context.`,
        set_description: `Enable or disable self-debug embed ingestion.`,
        already_set_title: `Self-Debug Already Set`,
        already_enabled_description: `Self-debug is already **enabled**.`,
        already_disabled_description: `Self-debug is already **disabled**.`,
        success_title: `Self-Debug Updated`,
        enabled_success: `Self-debug is now **enabled**. I will load my error and diagnostic embeds into context as [System: ...] messages.`,
        disabled_success: `Self-debug is now **disabled**. My error and diagnostic embeds will no longer be loaded into context.`,
      },
      maxmsgfetch: {
        description: `Set recent messages fetched for context (20-100, default: 80).`,
        limit_description: `Recent messages to fetch for context (20-100, default: 80).`,
        limit: {
          description: `Set max recent messages fetched for context (default: 80).`,
          limit_description: `Recent messages to fetch for context (20-100, default: 80).`,
          invalid_range_title: `Invalid Limit`,
          invalid_range_description: `Limit must be between {min} and {max}.`,
          already_set_title: `Already Set`,
          already_set_description: `Message fetch limit is already set to **{limit}**.`,
          success_title: `Message Fetch Limit Updated`,
          success_description: `I will now fetch up to **{limit}** recent messages for context.`,
        },
      },
      multitrigger: {
        description: `Manage personas triggered per message (default: 3).`,
        limit_description: `Max triggered personas per message (1-10, default: 3).`,
        limit: {
          description: `Set max personas triggered per message (default: 3).`,
          limit_description: `Max triggered personas per message (1-10, default: 3).`,
          invalid_range_title: `Invalid Limit`,
          invalid_range_description: `Limit must be between {min} and {max}.`,
          already_set_title: `Already Set`,
          already_set_description: `Multi-trigger limit is already set to **{limit}**.`,
          success_title: `Multi-Trigger Limit Updated`,
          success_description: `Per-message persona trigger limit set to **{limit}**.`,
        },
      },
      voice: {
        description: `Manage persona voice settings.`,
        transcripts: {
          description: `Toggle voice transcript chat mode.`,
          set_description: `Enable to post transcripts as chat messages; disable to use internal cache.`,
          already_set_title: `Already Set`,
          already_enabled_description: `Voice transcript chat mode is already enabled for this server.`,
          already_disabled_description: `Voice transcript chat mode is already disabled for this server.`,
          success_title: `Voice Transcript Mode Updated`,
          enabled_success: `Voice transcript chat mode is now **enabled**. Voice messages will be transcribed and posted as visible chat messages via webhook. Audio will not be passed to the AI directly.`,
          disabled_success: `Voice transcript chat mode is now **disabled**. Transcripts will be handled internally as before.`,
        },
        elevenlabs: {
          description: `Choose an ElevenLabs voice for a persona.`,
          select_persona_title: `Select Persona Voice Target`,
          no_key_title: `No ElevenLabs API Key Set`,
          no_key_description: `An ElevenLabs key is required before choosing persona voices. Set one first with \`/optionalkey elevenlabs set\`.`,
          voice_fetch_failed_title: `Voice List Unavailable`,
          voice_fetch_failed_description: `I couldn't load the available ElevenLabs voices for this server. Please check the configured key and try again.`,
          no_voices_title: `No Voices Available`,
          no_voices_description: `The configured ElevenLabs account did not return any usable voices.`,
          modal_title: `Select ElevenLabs Voice`,
          select_label: `Voice`,
          select_description: `Choose the voice this persona should use for generated voice messages.`,
          select_placeholder: `Choose a voice...`,
          clear_choice_label: `Disable Voice`,
          clear_choice_description: `Remove the current ElevenLabs voice from this persona.`,
          voice_available_description: `Available voice`,
          success_title: `Persona Voice Updated`,
          success_description: `**{persona}** will now use **{voice}** for ElevenLabs voice messages.`,
          cleared_title: `Persona Voice Cleared`,
          cleared_description: `Removed the ElevenLabs voice from **{persona}**.`,
        },
      },
      model: {
        text: {
          description: `Change the underlying AI model that I use.`,
          modal_title: `Select AI Model`,
          select_label: `AI Model`,
          select_description: `Choose the AI model for me to use. Check your AI provider's website for pricing of non-free models.`,
          select_placeholder: `Choose a model...`,
          no_api_key_title: `No API Key Set`,
          no_api_key_description: `An API key must be configured before changing models. Please use \`/config apikey set\` to set an API key first.`,
          no_models_title: `No Models Found`,
          no_models_description: `Could not load available AI models from the database.`,
          invalid_model_title: `Invalid Model`,
          invalid_model_description: `The selected model name is not valid or available.`,
          already_selected_title: `Model Already Selected`,
          already_selected_description: `I'm already using the \`{model_name}\` model.`,
          validating_api_key_compatibility_title: `Validating API Key`,
          validating_api_key_compatibility: `Validating API key compatibility with new provider...`,
          api_key_incompatible_title: `API Key Incompatible`,
          api_key_incompatible_description: `The current API key is not compatible with the {model_name} model from {provider}. Please set a valid API key for {provider} using \`/config apikey set\`.`,
          validation_error_title: `Validation Error`,
          validation_error_description: `An error occurred while validating API key compatibility. Please try again.`,
          success_title: `Model Updated`,
          success_description: `I will now use the \`{model_name}\` model (previously \`{previous_model}\`).`,
          // Custom provider reconfiguration messages
          custom_updated_title: `Custom Model Capabilities Updated`,
          custom_updated_description: `Your custom model has been reconfigured.\n\n**Model Name:** \`{model_name}\`\n**Enabled Capabilities:** {capabilities}`,
          // Scope option labels and success messages (scope = global | channel | persona)
          scope_description: `Set the scope for this model change (global, channel, or persona).`,
          scope_global: `Global (server default)`,
          scope_channel: `Channel (this channel only)`,
          scope_persona: `Persona (specific persona only)`,
          scope_set_channel_success: `Model for {channel} set to **{model}**`,
          scope_set_persona_success: `Model for **{persona}** set to **{model}**`,
          // Other-model configuration
          other_model_prompt_title: `Configure Custom OpenRouter Model`,
          other_model_prompt_description: `You've selected **other-model**.\n\nClick the button below and enter your OpenRouter model codename (e.g., \`xai/grok-2\`, \`openrouter/free\`, \`nvidia/nemotron-4-340b-instruct\`).`,
          other_model_modal_title: `Enter OpenRouter Model`,
          other_model_model_label: `OpenRouter Model Codename`,
          other_model_model_placeholder: `xai/grok-2`,
          other_model_validating_title: `Validating Model`,
          other_model_validating_description: `Fetching capabilities for \`{model_name}\` from OpenRouter...`,
          other_model_validation_failed_title: `Model Not Found`,
          other_model_validation_failed_description: `Could not find \`{model_name}\` on OpenRouter. Check the model ID is correct and try again.`,
          other_model_configured_title: `Custom Model Configured`,
          other_model_configured_description: `Your custom OpenRouter model is now set to \`{model_name}\`.\n\n**Detected Capabilities:** {capabilities}`,
        },
        embedding: {
          description: `Change the embedding model used for document retrieval.`,
          modal_title: `Select Embedding Model`,
          select_label: `Embedding Model`,
          select_description: `Choose the embedding model for document search.`,
          select_placeholder: `Choose a model...`,
          no_api_key_title: `No API Key Set`,
          no_api_key_description: `An API key must be configured before changing embedding models. Please use \`/config apikey set\` first.`,
          no_models_title: `No Embedding Models Available`,
          no_models_description: `No embedding models are available for provider {provider}.`,
          invalid_model_title: `Invalid Model`,
          invalid_model_description: `The selected embedding model is not valid or available.`,
          already_selected_title: `Model Already Selected`,
          already_selected_description: `I'm already using the \`{model_name}\` embedding model.`,
          reembed_started_title: `Re-embedding Documents`,
          reembed_started_description: `Rebuilding document embeddings with the new model. This may take a moment...`,
          success_title: `Embedding Model Updated`,
          success_description: `Embedding model changed to \`{model_name}\` (previously \`{previous_model}\`).`,
          current_none: `None`,
        },
        fallback: {
          description: `Set backup models to use if the primary model fails.`,
          modal_title: `Set Fallback Models`,
          slot_1_label: `Fallback Model 1 (Required)`,
          slot_2_label: `Fallback Model 2`,
          slot_3_label: `Fallback Model 3`,
          slot_4_label: `Fallback Model 4`,
          slot_5_label: `Fallback Model 5`,
          select_placeholder: `Choose a model...`,
          no_models_title: `No Models Available`,
          no_models_description: `There are no models available for your current provider.`,
          custom_provider_title: `Not Supported`,
          custom_provider_description: `Fallback models are not supported for custom providers.`,
          primary_conflict_title: `Invalid Selection`,
          primary_conflict_description: `One or more selected fallback models matches the server's primary model \`{model}\`. Please choose different models.`,
          success_title: `Fallback Models Updated`,
          success_description: `Fallback order:\n{model_list}`,
          cleared_title: `Fallback Models Cleared`,
          cleared_description: `No fallback models are configured for this server.`,
        },
        image: {
          description: `Change the image generation model for this server.`,
          modal_title: `Select Image Generation Model`,
          select_label: `Image Model`,
          select_description: `Choose the image generation model. Check your AI provider for pricing.`,
          select_placeholder: `Choose an image model...`,
          no_api_key_title: `No API Key Set`,
          no_api_key_description: `An API key must be configured before changing image models.`,
          no_models_title: `No Image Models Available`,
          no_models_description: `Your current text model provider ({provider}) does not support image generation. Switch to Google or OpenRouter using \`/config apikey set\` first.`,
          invalid_model_description: `The selected image model is not valid or available.`,
          already_selected_title: `Model Already Selected`,
          already_selected_description: `Already using the \`{model_name}\` image model.`,
          success_title: `Image Model Updated`,
          success_description: `Image generation will now use the \`{model_name}\` model (previously \`{previous_model}\`).`,
          current_none: `None`,
        },
        vision: {
          description: `Set a dedicated vision model for image analysis when your chat model can't see images.`,
          modal_title: `Select Vision Model`,
          select_label: `Vision Model`,
          select_description: `Choose a vision-capable model to analyze images on behalf of your chat model.`,
          select_placeholder: `Choose a vision model...`,
          no_api_key_title: `No API Key Set`,
          no_api_key_description: `An API key must be configured before setting a vision model. Please use \`/config apikey set\` first.`,
          no_models_title: `No Vision Models Available`,
          no_models_description: `Your current provider ({provider}) has no vision-capable models. Switch to a provider with vision models first.`,
          invalid_model_title: `Invalid Model`,
          invalid_model_description: `The selected vision model is not valid or available.`,
          already_selected_title: `Model Already Selected`,
          already_selected_description: `Already using \`{model_name}\` as the vision model.`,
          not_needed_title: `Vision Model Not Needed`,
          not_needed_description: `Your current chat model (\`{model_name}\`) already supports image vision. A separate vision model is only useful for non-vision chat models.`,
          success_title: `Vision Model Updated`,
          success_description: `Non-vision chat models will now use \`{model_name}\` to analyze images via the \`analyze_image\` tool.`,
          success_no_tools_description: `Vision model set to \`{model_name}\`, but your current chat model (\`{chat_model}\`) does not support **tool calling**. The vision model requires the \`analyze_image\` tool to work — switch to a chat model with tool support, or it won't be able to use it.`,
          cleared_title: `Vision Model Cleared`,
          cleared_description: `Vision model has been removed. Non-vision chat models will no longer be able to analyze images.`,
          clear_option: `None (disable vision tool)`,
        },
      },
      rename: {
        description: `Change my name on this server.`,
        modal_title: `Rename Persona`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona to rename.`,
        persona_select_placeholder: `Select a persona...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        new_name_input_label: `New Name`,
        new_name_input_description: `Enter the new name (2-32 characters).`,
        new_name_input_placeholder: `Enter a new persona name...`,
        option_description: `My new name (2-32 characters).`,
        invalid_length_title: `Invalid Name Length`,
        invalid_length: `Name must be between 2 and 32 characters.`,
        already_set_title: `Name Already Set`,
        already_set_description: `My name is already set to \`{nickname}\`.`,
        success_title: `Name Updated`,
        success_description: `My name has been changed from \`{old_nickname}\` to \`{new_nickname}\`.`,
        success_with_trigger_description: `My name has been changed from \`{old_nickname}\` to \`{new_nickname}\`. Trigger words updated accordingly.`,
        success_with_discord_description: `My name has been changed from \`{old_nickname}\` to \`{new_nickname}\`, and my server nickname has been updated!`,
        success_with_trigger_and_discord_description: `My name has been changed from \`{old_nickname}\` to \`{new_nickname}\`. Trigger words and server nickname updated!`,
        nickname_update_failed_footer: `Note: Server nickname update failed (may require "Change Nickname" permission).`,
        partial_success_title: `Name Updated with Issues`,
        partial_success_description: `My name has been changed to \`{new_nickname}\`, but some trigger word updates failed.`,
      },
      setup: {
        description: `Start the initial setup process. Configure AI provider and personality.`,
        no_presets_found: `No personality presets found in the database, please report through \`/support discord\`.`,
        modal_title: `Initial Setup`,
        api_provider_label: `API Provider`,
        api_provider_description: `Please choose the provider of the LLM of your choice`,
        api_provider_placeholder: `Choose a provider...`,
        api_key_label: `API Key`,
        api_key_description: `This key will be securely stored. Use the '/help apikey' command for instructions in getting one`,
        api_key_description_with_custom: `API Key, or OpenAI endpoint URL if using Custom (e.g., http://localhost:11434/v1)`,
        api_key_placeholder: `Do NOT share this key with anyone`,
        preset_label: `Personality Preset`,
        preset_description: `Choose a personality preset`,
        preset_placeholder: `Choose a personality...`,
        humanizer_label: `Humanizer Degree`,
        humanizer_description: `How 'human-like' should I reply?`,
        humanizer_placeholder: `Select humanization level...`,
        humanizer_option_none_label: `None`,
        humanizer_option_none_desc: `Raw AI output: no delays, full punctuation, immediate responses.`,
        humanizer_option_light_label: `Light`,
        humanizer_option_light_desc: `Basic guidance: uses 0-2 emojis, responds concisely. No typing simulation.`,
        humanizer_option_default_label: `Default`,
        humanizer_option_default_desc: `Balanced: typing indicators and thinking pauses between messages.`,
        humanizer_option_heavy_label: `Heavy`,
        humanizer_option_heavy_desc: `Maximum: sentence-level chunking with typing delays, casual lowercased text.`,
        humanizer_field: `Humanizer`,
        humanizer_invalid: `Invalid humanizer degree. Please select None, Light, Default, or Heavy.`,
        timezone_label: `Timezone Offset`,
        timezone_description: `UTC offset in hours. Examples: 8 or +8 (Singapore), -5 (New York), 0 (London). Leave empty for UTC.`,
        timezone_placeholder: `e.g., 8, -5, 0`,
        timezone_invalid_format: `Error: Invalid timezone format. Please enter a number like 8, -5, or 0. You provided: {provided}`,
        timezone_out_of_range: `Error: Timezone offset must be between {min} and {max}. You provided: {provided}`,
        api_key_invalid: `Error: The API key provided is too short or invalid.`,
        api_key_validating: `Validating API key...`,
        api_key_invalid_api: `Error: Provider rejected the API key. Please ensure it's correct.`,
        preset_invalid: `Error: Invalid preset name. Please enter one of the available preset names exactly: {available}`,
        config_invalid: `Error: Internal configuration validation failed. Please report this.`,
        setup_failed_description: `Error: Failed to save the initial setup configuration to the database. Please try again.`,
        modal_values_missing: `Error: Some required values were not received from the setup form. Please try the setup command again.`,
        provider_invalid: `Error: Invalid API provider selected. Please choose from the available options.`,
        preset_not_found: `Error: The selected preset was not found in the database. Please try again.`,
        success_title: `🟢 Setup Complete!`,
        success_desc: `I am now configured for this server! To modify my configuration, use my \`/config\` and \`/server\` commands. Optional but recommended: run the \`/server initialize\` commands to optimize emoji and sticker metadata. You can also manage or delete your data anytime with \`/data\`. Here's a summary:`,
        success_desc_with_model: `I am now configured for this server! I will use the \`{model_name}\` model (the default for this provider). To modify my configuration, use my \`/config\` and \`/server\` commands. Optional but recommended: run the \`/server initialize\` commands to optimize emoji and sticker metadata. You can also manage or delete your data anytime with \`/data\`. Here's a summary:`,
        success_desc_dm: `I am now configured for this Direct Message. You can manage or delete your data anytime with \`/data\`. Here's a summary:`,
        success_desc_dm_with_model: `I am now configured for this Direct Message. I will use the \`{model_name}\` model (the default for this provider). You can manage or delete your data anytime with \`/data\`. Here's a summary:`,
        next_steps_title: `🟢 What Can I Do?`,
        next_steps_description: `Use {helpFeatures} to see all my features, or just ask me in chat! I can also tell you what slash commands are available.`,
        novelai_expressions_warning_field: `⚠️ Expressions Disabled`,
        novelai_expressions_warning_value: `Emoji and sticker usage have been automatically disabled to keep NovelAI's context lean and stable. You can re-enable them anytime with .`,
        preset_field: `Personality Preset`,
        name_field: `My Name`,
        dm_context_explanation_title: `About Direct Messages`,
        dm_context_explanation: `I will still refer to this Direct Message as a "server". Meaning all "server" features work the same way, just privately here between us! Think of this Direct Message as a 1-on-1 server with me, therefore its server memories are my memories within here only.`,
        already_setup_title: `Already SeWt Up`,
        already_setup_description: `I am already set up for this server. To modify my configuration, please use other commands like \`/config\`, \`/teach\`, etc.

				If you wish to swap my provider, use the \`/config apikey set\` command.`,
      },
      params: {
        description: `Adjust AI sampling parameters for generation quality.`,
        temperature: {
          description: `Set response creativity/randomness (0-2.0, default: 1.0).`,
          value_description: `Value between 0 (deterministic) and 2.0 (very random). Default: 1.0.`,
          invalid_value_title: `Invalid Temperature`,
          invalid_value_description: `Temperature must be between {min} and {max}.`,
          already_set_title: `Temperature Already Set`,
          already_set_description: `The temperature is already set to \`{temperature}\`.`,
          success_title: `Temperature Updated`,
          success_description: `LLM temperature changed from \`{previous_temperature}\` to \`{temperature}\`.\n**Supported by:** Google, OpenRouter, NovelAI, DeepSeek, Z.ai, Custom, NVIDIA NIM`,
        },
        "top-p": {
          description: `Set top-P nucleus sampling threshold (default: 0.95).`,
          value_description: `Probability mass to sample from (0.0=very restricted, 1.0=full distribution). Default: 0.95.`,
          invalid_value_title: `Invalid Top-P Value`,
          invalid_value_description: `Top-P must be between {min} and {max}.`,
          already_set_title: `Top-P Already Set`,
          already_set_description: `Top-P is already set to \`{top_p}\`.`,
          success_title: `Top-P Updated`,
          success_description: `Top-P changed from \`{previous_top_p}\` to \`{top_p}\`.\n**Supported by:** Google, OpenRouter, NovelAI, DeepSeek, Z.ai, NVIDIA NIM`,
        },
        "top-k": {
          description: `Set top-K candidate token limit (default: 0).`,
          value_description: `Number of top tokens to sample from (0=disabled, max 40). Default: 0.`,
          invalid_value_title: `Invalid Top-K Value`,
          invalid_value_description: `Top-K must be between {min} and {max}.`,
          already_set_title: `Top-K Already Set`,
          already_set_description: `Top-K is already set to \`{top_k}\`.`,
          success_title: `Top-K Updated`,
          success_description: `Top-K changed from \`{previous_top_k}\` to \`{top_k}\`.\n**Supported by:** Google, OpenRouter, NovelAI, DeepSeek, Z.ai, NVIDIA NIM`,
        },
        "frequency-penalty": {
          description: `Set frequency penalty for repeated tokens (default: 0.0).`,
          value_description: `Penalty for frequent tokens (-2.0 to 2.0; exact 2.0 saves as 1.99). Default: 0.0.`,
          invalid_value_title: `Invalid Frequency Penalty`,
          invalid_value_description: `Frequency penalty must be between {min} and {max}.`,
          already_set_title: `Frequency Penalty Already Set`,
          already_set_description: `Frequency penalty is already set to \`{frequency_penalty}\`.`,
          success_title: `Frequency Penalty Updated`,
          success_description: `Frequency penalty changed from \`{previous_frequency_penalty}\` to \`{frequency_penalty}\`.\n**Supported by:** OpenRouter, NovelAI, DeepSeek, Z.ai, NVIDIA NIM`,
        },
        "presence-penalty": {
          description: `Set presence penalty for repeated topics (default: 0.0).`,
          value_description: `Penalty for repeated topics (-2.0 to 2.0; exact 2.0 saves as 1.99). Default: 0.0.`,
          invalid_value_title: `Invalid Presence Penalty`,
          invalid_value_description: `Presence penalty must be between {min} and {max}.`,
          already_set_title: `Presence Penalty Already Set`,
          already_set_description: `Presence penalty is already set to \`{presence_penalty}\`.`,
          success_title: `Presence Penalty Updated`,
          success_description: `Presence penalty changed from \`{previous_presence_penalty}\` to \`{presence_penalty}\`.\n**Supported by:** OpenRouter, NovelAI, DeepSeek, Z.ai, NVIDIA NIM`,
        },
        "min-p": {
          description: `Set min-P minimum probability threshold (default: 0.0).`,
          value_description: `Minimum token probability relative to top token (0.0=disabled, 1.0=most restricted). Default: 0.0.`,
          invalid_value_title: `Invalid Min-P Value`,
          invalid_value_description: `Min-P must be between {min} and {max}.`,
          already_set_title: `Min-P Already Set`,
          already_set_description: `Min-P is already set to \`{min_p}\`.`,
          success_title: `Min-P Updated`,
          success_description: `Min-P changed from \`{previous_min_p}\` to \`{min_p}\`.\n**Supported by:** OpenRouter, NovelAI, DeepSeek, Z.ai, NVIDIA NIM`,
        },
      },
      logitbias: {
        description: `Manage saved logit bias entries for supported models.`,
        add: {
          description: `Add comma-separated logit bias entries with one shared bias value.`,
          modal_title: `Add Logit Bias`,
          terms_label: `Words / Token IDs`,
          terms_description: `Comma-separated values. Words are tokenized for the active model and refreshed again when the model changes. Example: Sorry, apology, 50256`,
          terms_placeholder: `e.g. Sorry, apology, 50256`,
          bias_label: `Bias Value`,
          bias_description: `Number from -100 to 100. Example: -100`,
          bias_placeholder: `e.g. -100`,
          empty_terms_title: `No Entries Provided`,
          empty_terms_description: `Please enter at least one comma-separated word or token ID.`,
          term_too_long_title: `Entry Too Long`,
          term_too_long_description: `Each entry must be at most {max_length} characters long.`,
          invalid_bias_title: `Invalid Bias Value`,
          invalid_bias_description: `Bias must be a number between {min} and {max}.`,
          already_set_title: `No Logit Bias Changes`,
          already_set_description: `All provided entries already exist with that same bias value.`,
          success_title: `Logit Bias Updated`,
          success_description: `Added **{added_count}** new entry(s) and updated **{updated_count}** existing entry(s).\nTotal saved: **{total_count}**\nRuntime-ready for the current model: **{runtime_ready_count}**`,
        },
        remove: {
          description: `Remove saved logit bias entries.`,
          clearall_description: `Clear all saved logit bias entries without opening the modal.`,
          modal_title: `Remove Logit Bias`,
          checkbox_label: `Logit Bias Entries`,
          checkbox_label_continued: `Logit Bias Entries (Continued)`,
          checkbox_description: `Uncheck any entries you want to remove.`,
          none_title: `No Logit Bias Entries`,
          none_description: `This server has no saved logit bias entries.`,
          select_page_title: `Select Logit Bias Page`,
          select_page_description: `This server has **{total_entries}** saved logit bias entries across **{total_pages}** pages. Choose a page to edit.`,
          too_many_title: `Too Many Logit Bias Pages`,
          too_many_description: `This server has **{total_entries}** saved logit bias entries across **{total_pages}** pages. The current page selector supports up to **{max_pages}** pages.`,
          no_removals_title: `No Logit Bias Entries Removed`,
          no_removals_description: `No entries were unchecked. Saved logit bias entries remain unchanged.`,
          success_title: `Logit Bias Entries Updated`,
          success_description: `Removed **{removed_count}** entry(s). **{remaining_count}** entry(s) remain saved.`,
          clearall_success_title: `Logit Bias Cleared`,
          clearall_success_description: `Cleared all saved logit bias entries (**{removed_count}** removed).`,
        },
        upload: {
          description: `Upload SillyTavern-style logit bias JSON entries.`,
          file_description: `A .json file containing logit bias objects with text and value fields.`,
          invalid_file_title: `Invalid File`,
          invalid_format: `The attachment must be a JSON file.`,
          file_too_large_title: `File Too Large`,
          file_too_large_description: `The uploaded file must be {max_size} MB or smaller.`,
          download_failed_title: `Download Failed`,
          download_failed_description: `I could not download the uploaded file. Please try again.`,
          invalid_json_title: `Invalid JSON`,
          invalid_json_description: `The uploaded file is not valid JSON.`,
          invalid_schema_title: `Invalid Logit Bias Format`,
          invalid_schema_description: `Expected a SillyTavern-style entry or array of entries with \`text\` and \`value\`. Bias must be between {min} and {max}, and text must be at most {max_length} characters.`,
          no_entries_title: `No Entries Found`,
          no_entries_description: `The uploaded file did not contain any valid logit bias entries.`,
          already_set_title: `No Logit Bias Changes`,
          already_set_description: `All uploaded entries already exist with the same saved bias values.`,
          success_title: `Logit Bias Imported`,
          success_description: `Added **{added_count}** new entry(s) and updated **{updated_count}** existing entry(s).\nTotal saved: **{total_count}**\nRuntime-ready for the current model: **{runtime_ready_count}**`,
        },
      },
      timezone: {
        description: `Set your server's timezone offset from UTC (default: 0 / UTC).`,
        value_description: `UTC offset hours (default: 0). Examples: 8, -5, 0, 9.`,
        invalid_value_title: `Invalid Timezone Offset`,
        invalid_value_description: `Timezone offset must be between {min} and {max} hours.`,
        already_set_title: `Timezone Already Set`,
        already_set_description: `The timezone is already set to \`{timezone}\`.`,
        success_title: `Timezone Updated`,
        success_description: `Server timezone changed from \`{previous_timezone}\` to \`{timezone}\`.`,
      },
      permissions: {
        description: `Configure my core behavior permissions on this server.`,
        option_description: `The specific permission to configure.`,
        selfteaching_option: `Self-Teaching`,
        personalization_option: `Personalization (Memories/Nicknames)`,
        emojiusage_option: `Emoji Usage`,
        stickerusage_option: `Sticker Usage`,
        websearch_option: "Web Search Permission",
        pinmessage_option: "Pin Messages",
        imagegen_option: "Image Generation",
        hiderespondembed_option: "Hide Response Embeds",
        hideimpersonationembeds_option: "Hide Impersonation Embeds",
        voicemessage_option: "Voice Messages (ElevenLabs)",
        permission_choice_selfteaching: `Self-Teaching`,
        permission_choice_personalization: `Personalization (Memories/Nicknames)`,
        permission_choice_emojiusage: `Emoji Usage`,
        permission_choice_stickerusage: `Sticker Usage`,
        permission_choice_websearch: "Web Search Permission",
        permission_choice_pinmessage: "Pin Messages",
        permission_choice_imagegen: "Image Generation",
        permission_choice_hiderespondembed: "Hide Response Embeds",
        // Short option descriptions shown inside the select menu dropdown
        selfteaching_desc: "Learn from server conversations",
        personalization_desc: "Personal memories & nicknames",
        emojiusage_desc: "Use emojis in responses",
        stickerusage_desc: "Send sticker reactions",
        websearch_desc: "Browse the web for information",
        pinmessage_desc: "Pin important messages",
        imagegen_desc: "Generate images on request",
        hiderespondembed_desc: "Hide /bot respond success embed",
        hideimpersonationembeds_desc: "Hide persona impersonation notices",
        voicemessage_desc: "Send ElevenLabs TTS voice messages",
        // Checkbox select menu UI strings
        select_placeholder: "Select permissions to enable...",
        select_embed_title: "Configure Permissions",
        select_embed_description:
          "Select which permissions to enable. Checked = active, unchecked = disabled.",
        no_changes_title: "No Changes Made",
        no_changes_description:
          "All permissions are already at the selected values.",
        timed_out_title: "Selection Timed Out",
        timed_out_description:
          "The permission menu timed out. No changes were applied.",
        set_description: `Enable or disable this permission for me.`,
        already_set_title: `Permission Already Set`,
        already_enabled_description: `The permission \`{permission_type}\` is already **enabled**.`,
        already_disabled_description: `The permission \`{permission_type}\` is already **disabled**.`,
        success_title: `Permissions Updated`,
        success_description: `Updated **{count}** permission(s).\n`,
        enabled_success: `My permission for \`{permission_type}\` is now **enabled**.`,
        disabled_success: `My permission for \`{permission_type}\` is now **disabled**.`,
      },
      uncensors: {
        description: `Configure optional uncensor behaviors for my prompts on this server.`,
        option_description: `Which uncensor setting to configure.`,
        injection_option: `Prompt Injection (18+ acknowledgement)`,
        unicode_spaces_option: `Unicode Space Replacement`,
        sanitize_option: `Sensitive Word Sanitization`,
        set_description: `Enable or disable this uncensor setting.`,
        already_set_title: `Uncensor Setting Already Set`,
        already_enabled_description: `The uncensor setting \`{uncensor_type}\` is already **enabled**.`,
        already_disabled_description: `The uncensor setting \`{uncensor_type}\` is already **disabled**.`,
        success_title: `Uncensor Setting Updated`,
        enabled_success: `My uncensor setting \`{uncensor_type}\` is now **enabled**.`,
        disabled_success: `My uncensor setting \`{uncensor_type}\` is now **disabled**.`,
        injection_ack_notice: `Note: By enabling this, you acknowledge that all server members are of legal age.`,
      },

      // System prompt management
      sysprompt: {
        description: `Manage custom system prompt for personality instructions`,
        change: {
          description: `Set a custom system prompt to guide my behavior`,
        },
        clear: {
          description: `Remove custom system prompt and use default system prompt`,
        },
        preset: {
          description: `Apply a preset system prompt`,
        },
      },
      prompt: {
        description: `Manage custom system prompt for personality instructions`,
        change: {
          description: `Set a custom system prompt to guide my behavior`,
          modal_title: `Set Custom System Prompt`,
          part1_label: `System Prompt (Part 1/4)`,
          part1_description: `Main instructions. Use {bot} for my name, {user} for the triggering user`,
          part1_placeholder: `e.g., {bot} is friendly and helpful...`,
          part2_label: `System Prompt (Part 2/4) - Optional`,
          part2_description: `Continuation of instructions (optional)`,
          part2_placeholder: `Additional instructions...`,
          part3_label: `System Prompt (Part 3/4) - Optional`,
          part3_description: `Continuation of instructions (optional)`,
          part3_placeholder: `More instructions...`,
          part4_label: `System Prompt (Part 4/4) - Optional`,
          part4_description: `Continuation of instructions (optional)`,
          part4_placeholder: `Final instructions...`,
          empty_prompt_title: `Empty System Prompt`,
          empty_prompt_description: `The system prompt cannot be empty. Please provide at least some instructions in Part 1.`,
          success_title: `System Prompt Updated`,
          success_description: `Custom system prompt has been set successfully:\n\`\`\`\n{preview}...\n\`\`\``,
        },
        clear: {
          description: `Remove custom system prompt and use default system prompt`,
          no_custom_prompt_title: `No Custom Prompt Set`,
          no_custom_prompt_description: `There is no custom system prompt configured. Currently using the default prompt:\n\`\`\`\n{defaultPrompt}\n\`\`\``,
          success_title: `System Prompt Cleared`,
          success_description: `Custom system prompt has been cleared. Now using the default prompt:\n\`\`\`\n{defaultPrompt}\n\`\`\``,
        },
        preset: {
          description: `Apply a preset system prompt`,
          modal_title: `Select System Prompt Preset`,
          selection_label: `Choose a preset`,
          selection_placeholder: `Pick a preset prompt style...`,
          success_title: `✓ Preset Applied`,
          success_description: `System prompt preset applied: **{presetName}**\nPreview:\n\`\`\`\n{preview}...\n\`\`\``,
          no_presets_title: `No Presets Available`,
          no_presets_description: `No system prompt presets found. Please contact the bot administrator.`,
          invalid_preset_title: `Invalid Preset`,
          invalid_preset_description: `The selected preset could not be found. Please try again.`,
        },
      },

      // Random Trigger management (timer-based probabilistic auto-trigger)
      randomtrigger: {
        add: {
          description: `Add a probabilistic timer-based auto-trigger for a channel.`,
          channel_description: `The channel where spontaneous messages will be sent.`,
          timer_hours_description: `How often to roll the dice (in hours, minimum 1).`,
          random_offset_range_description: `Optional +/- random offset range in hours for each timer reset (minimum 0).`,
          chance_description: `Probability of firing each roll (1–100%).`,
          silence_threshold_description: `Skip if channel had activity within this many hours (optional).`,
          failure_threshold_description: `Force-fire after this many consecutive dice misses, resetting the counter (optional).`,
          modal_title: `Configure Random Trigger`,
          persona_select_label: `Persona`,
          persona_select_description: `Which persona will speak. "Random" picks one each time.`,
          persona_select_placeholder: `Select a persona...`,
          persona_random_label: `Random (pick each time)`,
          respond_to_self_label: `Respond to Self`,
          respond_to_self_description: `Fire even if this persona spoke last?`,
          respond_to_self_yes: `Yes`,
          respond_to_self_no: `No`,
          prompt_label: `Custom Prompt (Optional)`,
          prompt_description: `Extra instructions injected for this trigger's messages.`,
          prompt_placeholder: `e.g., Start a topic about the weather...`,
          cap_reached_title: `Trigger Limit Reached`,
          cap_reached_description: `This server has reached the maximum of {max} random triggers. Remove one first.`,
          override_title: `Trigger Updated`,
          override_description: `A trigger already existed for {persona} in {channel}, and it has been updated with the new settings.`,
          success_title: `Random Trigger Added`,
          success_description: `I will check {channel} every **{timer_hours}h** with a **{chance}%** chance of speaking as **{persona}**.{offset_suffix}{silence_suffix}{failure_suffix}`,
          success_offset_suffix: ` Each reset adds a random offset of up to **+/-{random_offset_range}h**.`,
          success_silence_suffix: ` Skipped if active within **{silence_threshold}h**.`,
          success_failure_suffix: ` Force-fires after **{failure_threshold}** consecutive misses.`,
        },
        remove: {
          description: `Remove an existing random trigger from this server.`,
          modal_title: `Remove Random Triggers`,
          checkbox_label: `Random Triggers`,
          checkbox_label_continued: `Random Triggers (Continued)`,
          checkbox_description: `Uncheck any random triggers you want to remove.`,
          select_label: `Trigger to Remove`,
          select_description: `Select the random trigger you want to delete.`,
          select_placeholder: `Select a trigger...`,
          none_title: `No Triggers Found`,
          none_description: `This server has no random triggers configured.`,
          no_removals_title: `No Random Triggers Removed`,
          no_removals_description: `No random triggers were unchecked. Random triggers remain unchanged.`,
          success_title: `Random Triggers Updated`,
          success_description: `Removed the following random triggers.\n{triggers_removed}`,
        },
      },

      // Model override removal (subcommand group)
      remove: {
        description: `Remove overrides and fallbacks from the server configuration.`,
        modeloverride: {
          description: `Remove channel and persona model overrides.`,
          modal_title: `Remove Model Overrides`,
          channel_checkbox_label: `Channel Overrides`,
          channel_checkbox_label_continued: `Channel Overrides (Continued)`,
          channel_checkbox_description: `Uncheck any channel overrides you want to remove.`,
          persona_checkbox_label: `Persona Overrides`,
          persona_checkbox_label_continued: `Persona Overrides (Continued)`,
          persona_checkbox_description: `Uncheck any persona overrides you want to remove.`,
          none_title: `No Model Overrides`,
          none_description: `This server has no channel or persona model overrides configured.`,
          too_many_title: `Too Many Model Overrides`,
          too_many_description: `This server has **{channel_count}** channel override(s) and **{persona_count}** persona override(s) (**{total_count}** total). Discord only allows **{max_groups}** checkbox groups (**{max_entries}** total options) per modal.`,
          no_removals_title: `No Model Overrides Removed`,
          no_removals_description: `No overrides were unchecked. Model overrides remain unchanged.`,
          success_title: `Model Overrides Updated`,
          success_description: `Removed the following model overrides.\n{removed_overrides}`,
        },
        modelfallback: {
          description: `Remove models from the fallback chain.`,
          modal_title: `Remove Fallback Models`,
          checkbox_label: `Fallback Models`,
          checkbox_description: `Uncheck any fallback models you want to remove. Checked models keep their current order.`,
          none_title: `No Fallbacks Configured`,
          none_description: `This server has no fallback models configured.`,
          no_removals_title: `No Fallback Models Removed`,
          no_removals_description: `No fallback models were unchecked. The fallback chain remains unchanged.`,
          success_title: `Fallback Chain Updated`,
          success_description: `Removed the following fallback model(s): {models_removed}\n{remaining_count} fallback(s) remaining.`,
        },
      },
      mcp: {
        description: `Manage remote MCP (Model Context Protocol) tool servers`,
        add: {
          description: `Register a new remote MCP server for this guild. Use /help mcp for a setup guide.`,
          modal_title: `Add MCP Server`,
          name_label: `Server Name`,
          name_placeholder: `my-mcp-server`,
          url_label: `Server URL`,
          url_placeholder: `https://mcp.example.com/sse`,
          auth_token_label: `Auth Token (Optional)`,
          auth_token_placeholder: `Bearer token or Smithery API key (leave blank if none)`,
          server_type_label: `Server Type (Optional)`,
          server_type_description: `What this server replaces (disables matching built-in tools)`,
          server_type_placeholder: `Select a server type...`,
          none_option: `General Purpose`,
          none_option_description: `No built-in tools will be disabled`,
          web_search_option: `Web Search`,
          web_search_option_description: `Disables built-in Brave and DuckDuckGo search tools`,
          url_fetcher_option: `URL Fetcher`,
          url_fetcher_option_description: `Disables built-in URL fetch tool`,
          invalid_input_title: `Missing Input`,
          invalid_input_description: `Both server name and URL are required.`,
          invalid_name_title: `Invalid Server Name`,
          invalid_name_description: `Server name must be 1-32 characters using only letters, numbers, and hyphens. It must start with a letter or number.`,
          invalid_url_title: `Invalid URL`,
          invalid_url_invalid_format_description: `The MCP server URL is not a valid URL.`,
          invalid_url_protocol_description: `The MCP server URL must use HTTP or HTTPS.`,
          invalid_url_http_localhost_only_description: `In development, HTTP is only allowed for localhost MCP servers. Use HTTPS for remote servers.`,
          invalid_url_https_required_description: `Production only allows HTTPS MCP servers with TLS.`,
          invalid_url_localhost_blocked_description: `Production does not allow localhost MCP servers.`,
          invalid_url_dns_failed_description: `The hostname \`{hostname}\` could not be resolved from this server.`,
          invalid_url_private_address_description: `Production only allows publicly routable MCP hosts. The hostname resolved to blocked address \`{address}\`.`,
          limit_reached_title: `Server Limit Reached`,
          limit_reached_description: `This guild has reached the maximum of {max} MCP servers. Remove an existing server before adding a new one.`,
          connection_failed_title: `Connection Failed`,
          connection_failed_description: `Could not connect to the MCP server.\n**Error:** {error}`,
          duplicate_name_title: `Duplicate Name`,
          duplicate_name_description: `An MCP server named "{name}" already exists in this guild.`,
          success_title: `MCP Server Added`,
          success_description: `**{name}** has been registered successfully.\n**URL:** \`{url}\`\n**Tools discovered:** {tool_count} ({tool_names})\n\nOnly add MCP servers you trust.\nA malicious server may send misleading instructions, collect data sent to its tools, or return harmful or false results.`,
        },
        remove: {
          description: `Remove a registered MCP server from this guild.`,
          modal_title: `Remove MCP Servers`,
          checkbox_label: `Registered MCP Servers`,
          checkbox_label_continued: `Registered MCP Servers (Continued)`,
          checkbox_description: `Uncheck any MCP servers you want to remove.`,
          too_many_title: `Too Many MCP Servers`,
          too_many_description: `This guild has **{count}** registered MCP servers. Discord only allows **{max_groups}** checkbox groups (**{max_entries}** total options) per modal.`,
          no_removals_title: `No MCP Servers Removed`,
          no_removals_description: `No MCP servers were unchecked. Registered servers remain unchanged.`,
          not_found_title: `Server Not Found`,
          not_found_description: `No MCP server named "{name}" was found in this guild.`,
          success_title: `MCP Servers Updated`,
          success_description: `Removed and disconnected the following MCP servers.\n{servers_removed}`,
        },
        list: {
          description: `List all registered MCP servers for this guild.`,
          empty_title: `No MCP Servers`,
          empty_description: `This guild has no registered MCP servers. Use \`/config mcp add\` to register one.`,
          title: `Registered MCP Servers`,
          header_description: `**{count}** server(s) registered:\n\n{servers}`,
        },
        toggle: {
          description: `Enable or disable a registered MCP server.`,
          modal_title: `Toggle MCP Server`,
          select_label: `Select Server`,
          select_description: `Choose the MCP server to toggle`,
          select_placeholder: `Select a server to toggle...`,
          state_label: `Enable or Disable`,
          state_description: `Choose whether to enable or disable the server`,
          state_placeholder: `Select a state...`,
          currently_enabled: `Enabled`,
          currently_disabled: `Disabled`,
          enable_option: `Enable`,
          enable_option_description: `Enable this MCP server for tool calling`,
          disable_option: `Disable`,
          disable_option_description: `Disable this MCP server and disconnect it`,
          not_found_title: `Server Not Found`,
          not_found_description: `No MCP server named "{name}" was found in this guild.`,
          enabled_success_title: `MCP Server Enabled`,
          enabled_success_description: `MCP server "{name}" has been enabled and will be available for tool calling.`,
          disabled_success_title: `MCP Server Disabled`,
          disabled_success_description: `MCP server "{name}" has been disabled and disconnected.`,
        },
      },
    },

    optionalkey: {
      description: `Manage optional service API keys`,
      brave: {
        description: `Manage Brave Search API key`,
        set: {
          description: `Set the Brave Search API key for this server.`,
          key_description: `Your Brave Search API key.`,
          invalid_key_title: `Invalid API Key Format`,
          invalid_key_description: `The provided API key seems too short or invalid. Please provide a valid key.`,
          validating_key: `Validating Brave Search API key...`,
          validation_error_title: `API Key Validation Error`,
          validation_error_description: `An error occurred while validating the Brave Search API key. Please try again or check your connection.`,
          key_validation_failed_title: `Brave API Key Validation Failed`,
          key_validation_failed_description: `The provided Brave Search API key is not valid. Please check the key and try again.`,
          success_title: `Brave API Key Set`,
          success_description: `The Brave Search API key has been successfully validated, encrypted, and saved.`,
        },
        remove: {
          description: `Remove the currently configured Brave Search API key.`,
          no_key_title: `No Brave API Key Set`,
          no_key_description: `There is no Brave Search API key currently configured to remove.`,
          success_title: `Brave API Key Removed`,
          success_description: `The Brave Search API key has been successfully removed.`,
        },
      },
      google: {
        description: `Manage supplementary Google API key (for image inpainting)`,
        set: {
          description: `Set a Google API key for AI image segmentation. Not needed if Google is already your AI provider.`,
          key_description: `Your Google API key.`,
          invalid_key_title: `Invalid API Key Format`,
          invalid_key_description: `The provided API key seems too short or invalid. Please provide a valid Google API key.`,
          key_validation_failed_title: `Google API Key Validation Failed`,
          key_validation_failed_description: `The provided Google API key is not valid. Please check the key and try again.`,
          success_title: `Google API Key Set`,
          success_description: `The Google API key has been saved for AI image segmentation (inpainting). If your main provider is already Google, this key takes priority over it for segmentation.`,
        },
        remove: {
          description: `Remove the currently configured Google API key.`,
          no_key_title: `No Google API Key Set`,
          no_key_description: `There is no Google API key currently configured to remove.`,
          success_title: `Google API Key Removed`,
          success_description: `The Google API key has been successfully removed.`,
        },
      },
      novelai: {
        description: `Manage supplementary NovelAI API key (for image generation)`,
        set: {
          description: `Set a NovelAI API key for image generation. Not needed if NovelAI is already your AI provider.`,
          key_description: `Your NovelAI API key.`,
          disable_other_imggen_description: `If true, hides the standard image generation tool so only NovelAI image gen is available.`,
          invalid_key_title: `Invalid API Key Format`,
          invalid_key_description: `The provided API key seems too short or invalid. Please provide a valid NovelAI API key.`,
          key_validation_failed_title: `NovelAI API Key Validation Failed`,
          key_validation_failed_description: `The provided NovelAI API key is not valid. Please check the key and ensure you have an active subscription.`,
          success_title: `NovelAI API Key Set`,
          success_description: `The NovelAI API key has been successfully validated, encrypted, and saved. NovelAI image generation is now available regardless of your active LLM provider.`,
          success_exclusive_description: `The NovelAI API key has been successfully validated, encrypted, and saved. NovelAI image generation is now the exclusive image generation tool for this server.`,
        },
        remove: {
          description: `Remove the currently configured NovelAI API key.`,
          no_key_title: `No NovelAI API Key Set`,
          no_key_description: `There is no NovelAI API key currently configured to remove.`,
          success_title: `NovelAI API Key Removed`,
          success_description: `The NovelAI API key and exclusive image generation setting have been removed.`,
        },
      },
      elevenlabs: {
        description: `Manage supplementary ElevenLabs API key (for speech and voice)`,
        set: {
          description: `Set an ElevenLabs API key for speech transcription and persona voice output.`,
          key_description: `Your ElevenLabs API key.`,
          invalid_key_title: `Invalid API Key Format`,
          invalid_key_description: `The provided API key seems too short or invalid. Please provide a valid ElevenLabs API key.`,
          key_validation_failed_title: `ElevenLabs API Key Validation Failed`,
          key_validation_failed_description: `The provided ElevenLabs API key is not valid. Please check the key and try again.`,
          success_title: `ElevenLabs API Key Set`,
          success_description: `The ElevenLabs API key has been successfully validated, encrypted, and saved. Voice transcription and persona voice output are now available where configured.`,
          success_voices_title: `Premade Voices (Free Tier)`,
          success_voices_description: `Premade voices work on the free plan. Browse the full list at [ElevenLabs Premade Voices](https://elevenlabs-sdk.mintlify.app/voices/premade-voices), then use {configVoiceElevenlabs} to assign one to each persona.`,
          success_custom_voices_title: `Library & Custom Voices (Paid)`,
          success_custom_voices_description: `Library voices and custom/cloned voices both require a paid ElevenLabs plan. Once added to your account, they will appear automatically in {configVoiceElevenlabs}.`,
          success_transcript_mode_title: `Voice Transcript Mode`,
          success_transcript_mode_description: `Use {configVoiceTranscripts} to post voice message transcripts as visible chat messages via webhook which saves re-processing credits and lets everyone see what was said.`,
        },
        remove: {
          description: `Remove the currently configured ElevenLabs API key.`,
          no_key_title: `No ElevenLabs API Key Set`,
          no_key_description: `There is no ElevenLabs API key currently configured to remove.`,
          success_title: `ElevenLabs API Key Removed`,
          success_description: `The ElevenLabs API key has been successfully removed.`,
        },
      },
    },

    // Server configuration commands (admin-only)
    server: {
      // RP channel management (subcommand group)
      rpchannel: {
        description: `Manage RP channels where emojis and stickers are always suppressed`,
        add: {
          description: `Add a channel to the RP channel list (disables emojis and stickers).`,
          channel_description: `The text channel to add to the RP channel list.`,
          success_title: `RP Channel Added`,
          success_description: `Successfully added \`{channel_name}\` to the RP channel list. Emojis and stickers will always be suppressed there.`,
          already_added_title: `Channel Already in List`,
          already_added_description: `The channel \`{channel_name}\` is already in the RP channel list.`,
        },
        remove: {
          description: `Remove a channel from the RP channel list.`,
          channel_description: `The text channel to remove from the RP channel list.`,
          success_title: `RP Channel Removed`,
          success_description: `Successfully removed \`{channel_name}\` from the RP channel list. Emojis and stickers will follow global settings there.`,
          not_found_title: `Channel Not Found`,
          not_found_description: `The channel \`{channel_name}\` is not in the RP channel list.`,
        },
      },
      // Auto-chat configuration (subcommand group)
      autotrigger: {
        description: `Manage auto-chat settings`,
        channels: {
          description: `Add or remove channels where I will automatically chat.`,
          channel_description: `The text channel to add or remove.`,
          action_description: `Whether to add or remove the channel.`,
          invalid_channel_title: `Invalid Channel Type`,
          invalid_channel_description: `Please select a standard text channel.`,
          already_added_title: `Channel Already Added`,
          already_added_description: `The channel \`{channel_name}\` is already in the auto-chat list.`,
          not_in_list_title: `Channel Not Found`,
          not_in_list_description: `The channel \`{channel_name}\` is not in the auto-chat list.`,
          added_title: `Auto-Chat Channel Added`,
          added_description: `Successfully added \`{channel_name}\` to the auto-chat channels.`,
          removed_title: `Auto-Chat Channel Removed`,
          removed_description: `Successfully removed \`{channel_name}\` from the auto-chat channels.`,
        },
        threshold: {
          description: `Set the shared auto-chat range for configured auto-chat channels.`,
          threshold_description: `Minimum messages before auto-chat, or 0 for always-reply mode.`,
          max_description: `Optional maximum messages before auto-chat. Leave empty to use the same value.`,
          invalid_range_title: `Invalid Threshold`,
          invalid_range_specific_description: `Use \`{always}\` for always-reply mode, or choose a range where both values are between \`{min}\` and \`{max}\` and max is at least min.`,
          success_title: `Auto-Chat Threshold Set`,
          success_description: `I will now automatically chat after \`{threshold}\` messages in designated channels.`,
          success_range_title: `Auto-Chat Range Set`,
          success_range_description: `I will now automatically chat after a random \`{min}\`-\`{max}\` messages in designated channels.`,
          success_always_title: `Auto-Chat Always-Reply Mode Set`,
          success_always_description: `Auto-chat threshold set to \`{threshold}\`. Configured auto-chat channels will now behave like always-reply for qualifying messages. Remove a channel to disable it there.`,
        },
      },
      // Trigger word management (subcommand group)
      trigger: {
        description: `Manage trigger words`,
        add: {
          description: `Add trigger words for a persona.`,
          word_description: `The word to add as a trigger.`,
          modal_title: `Add Trigger Words`,
          persona_select_label: `Persona`,
          persona_select_description: `Choose the persona to add triggers to.`,
          persona_select_placeholder: `Select a persona...`,
          triggers_input_label: `Trigger Words`,
          triggers_input_description: `Enter trigger words separated by commas ("," or "、").`,
          triggers_input_placeholder: `e.g., tomori, tomo`,
          main_persona_description: `Main Persona`,
          alter_persona_description: `Alter Persona`,
          no_triggers_title: `No Trigger Words`,
          no_triggers_description: `Please enter at least one trigger word.`,
          too_short_title: `Trigger Word Too Short`,
          too_short_description: `Trigger words must be at least 2 characters long.`,
          content_too_long_title: `Trigger Word Too Long`,
          content_too_long_description: `Trigger words cannot exceed {max_length} characters.`,
          already_exists_title: `Trigger Word Exists`,
          already_exists_description: `The word \`{word}\` is already in the trigger list.`,
          already_exists_multiple_description: `These trigger words already exist: {words}.`,
          limit_exceeded_title: `Trigger Word Limit Exceeded`,
          limit_exceeded_description: `This server can have up to {max_allowed} trigger words (currently has {current_count}). Please remove some trigger words with \`/server trigger delete\` before adding new ones.`,
          success_title: `Trigger Word Added`,
          success_description: `Added {added_count} trigger word(s) to {persona_name}: {added_words}. There are now {word_count} trigger words.`,
        },
        delete: {
          description: `Remove a word that makes me respond when mentioned.`,
          no_triggers_title: `No Trigger Words`,
          no_triggers_description: `There are no custom trigger words set to remove. Add some with \`/server trigger add\`.`,
          select_title: `Remove Trigger Word`,
          select_description: `Select the trigger word you want to remove`,
          trigger_words_label: `Trigger Words`,
          modal_title: `Remove Trigger Words`,
          checkbox_label: `Trigger Words`,
          checkbox_label_continued: `Trigger Words (Continued)`,
          checkbox_description: `Uncheck any trigger words you want to remove.`,
          select_label: `Trigger Word`,
          select_placeholder: `Choose a trigger word to remove`,
          no_removals_title: `No Trigger Words Removed`,
          no_removals_description: `No trigger words were unchecked. Trigger words remain unchanged.`,
          success_title: `Trigger Words Updated`,
          success_description: `Removed the following trigger word(s): {triggerWords}`,
        },
      },
      blacklist: {
        description: `Add or remove a member from the personalization blacklist.`,
        member_description: `The member to add or remove from the blacklist.`,
        action_description: `Whether to add or remove the member.`,
        personalization_disabled_title: `Personalization Disabled`,
        personalization_disabled_description: `Personalization is currently disabled server-wide. Enable it first with \`/config permissions\`.`,
        already_blacklisted_title: `Already Blacklisted`,
        already_blacklisted_description: `\`{user_name}\` is already on the personalization blacklist.`,
        not_blacklisted_title: `Not Blacklisted`,
        not_blacklisted_description: `\`{user_name}\` is not on the personalization blacklist.`,
        added_title: `Member Blacklisted`,
        added_description: `Added \`{user_name}\` to the personalization blacklist. Their personal memories and nickname won't be used.`,
        removed_title: `Member Unblacklisted`,
        removed_description: `Removed \`{user_name}\` from the personalization blacklist. Their personal memories and nickname can now be used.`,
        user_registration_failed_title: `User Registration Failed`,
        user_registration_failed_description: `Failed to register user in the database. Please try again.`,
        cannot_blacklist_bot_title: `Cannot Blacklist Bots`,
        cannot_blacklist_bot_description: `\`{user_name}\` is a bot and cannot be added to the personalization blacklist.`,
      },
      welcomechannel: {
        description: `Configure a welcome channel for new member greetings.`,
        channel_description: `The text channel where new members should be greeted.`,
        action_description: `Whether to add or remove the welcome channel.`,
        modal_title: `Configure Welcome Greeting`,
        persona_select_label: `Greet Persona`,
        persona_select_description: `Choose which persona should greet new members. Random picks one each time.`,
        persona_select_placeholder: `Select a persona...`,
        persona_random_label: `Random (Choose Each Join)`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        prompt_label: `Additional Prompt`,
        prompt_description: `How should I greet new users?`,
        prompt_placeholder: `Greet users by...`,
        empty_prompt_title: `Additional Prompt Required`,
        empty_prompt_description: `Please enter how I should greet new users.`,
        added_title: `Welcome Channel Updated`,
        added_description: `I will now greet new members in {channel} using **{persona}**.`,
        removed_title: `Welcome Channel Removed`,
        removed_description: `I will no longer send automated welcome greetings for new members.`,
        not_configured_title: `Welcome Channel Not Configured`,
        not_configured_description: `This server does not currently have a welcome channel configured.`,
      },
      thoughtlogs: {
        description: `Set or clear the server's thought-log channel.`,
        channel_description: `Text channel for reasoning summaries. Pick the same channel again to disable it.`,
        invalid_channel_title: `Invalid Channel`,
        invalid_channel_description: `Please choose a server text channel.`,
        set_title: `Thought Logs Enabled`,
        set_description: `Thought logs will now be posted in {channel}.`,
        updated_title: `Thought Logs Updated`,
        updated_description: `Thought logs will now be posted in {channel}.`,
        cleared_title: `Thought Logs Disabled`,
        cleared_description: `Thought logs will no longer be posted.`,
      },
      whitelist: {
        description: `Manage trigger whitelist (channels + roles; channels can inherit or override the global cooldown)`,
        channel: {
          description: `Add a channel to the whitelist, optionally overriding the global cooldown`,
          channel_description: `The channel to whitelist`,
          type_description: `Optional override: cooldown type for this channel`,
          length_description: `Optional override: cooldown length in seconds (0 = instant, no cooldown)`,
          invalid_channel_title: `Invalid Channel Type`,
          invalid_channel_description: `Only text channels can be whitelisted.`,
          already_set_title: `Already Set`,
          already_set_description: `Channel **{channel_name}** already has these exact whitelist settings.`,
          invalid_type_title: `Invalid Cooldown Type`,
          invalid_type_description: `The selected cooldown type is invalid. Please choose a valid option.`,
          invalid_length_title: `Invalid Cooldown Length`,
          invalid_length_description: `Cooldown length must be between **{min}** and **{max}** seconds.`,
          success_inherit_title: `Channel Whitelisted`,
          success_inherit_description: `Channel **{channel_name}** whitelisted and set to inherit this server's global cooldown.\n\n**Note:** When ANY channel is whitelisted, ONLY whitelisted channels can trigger the bot.`,
          success_title: `Channel Whitelisted`,
          success_description: `Channel **{channel_name}** whitelisted with a channel-specific **{cooldown_type}** cooldown of **{cooldown_length}** seconds.\n\n**Note:** When ANY channel is whitelisted, ONLY whitelisted channels can trigger the bot.`,
          success_instant_title: `Channel Whitelisted (Instant)`,
          success_instant_description: `Channel **{channel_name}** whitelisted with a channel-specific **{cooldown_type}** override (0 seconds = instant, no cooldown).\n\n**Note:** When ANY channel is whitelisted, ONLY whitelisted channels can trigger the bot.`,
        },
        role: {
          description: `Add or remove whitelisted roles that can trigger the bot`,
          role_description: `The role to add or remove from whitelist`,
          action_description: `Choose whether to add or remove this role`,
          action_add: `Add`,
          action_remove: `Remove`,
          invalid_role_title: `Invalid Role`,
          invalid_role_description: `The @everyone role cannot be used for role whitelist.`,
          already_set_title: `Already Set`,
          already_set_description: `Role {role_mention} is already in the whitelist.`,
          not_set_title: `Not Set`,
          not_set_description: `Role {role_mention} is not in the whitelist.`,
          success_add_title: `Role Whitelisted`,
          success_add_description: `Role {role_mention} can now trigger the bot when role whitelist is active.`,
          success_remove_title: `Role Removed from Whitelist`,
          success_remove_description: `Role {role_mention} has been removed from the whitelist.`,
        },
        remove: {
          description: `Remove channels or roles from whitelist`,
          modal_title: `Remove Whitelist Entries`,
          checkbox_label: `Whitelisted Channels`,
          checkbox_label_continued: `Whitelisted Channels (Continued)`,
          checkbox_description: `Uncheck any channels you want to remove from the whitelist.`,
          role_checkbox_label: `Whitelisted Roles`,
          role_checkbox_label_continued: `Whitelisted Roles (Continued)`,
          role_checkbox_description: `Uncheck any roles you want to remove from the whitelist.`,
          no_entries_title: `No Whitelist Entries`,
          no_entries_description: `There are no whitelisted channels or roles to remove.`,
          too_many_entries_title: `Too Many Whitelist Entries`,
          too_many_entries_description: `This server has **{channel_count}** whitelisted channels and **{role_count}** whitelisted roles. Discord only allows **{max_groups}** checkbox groups (**{max_entries}** total options) per modal.`,
          no_removals_title: `No Whitelist Entries Removed`,
          no_removals_description: `No whitelist entries were unchecked. The whitelist remains unchanged.`,
          success_title: `Whitelist Updated`,
          success_description: `Removed the following whitelist entries.\n**Channels:** {channels_removed}\n**Roles:** {roles_removed}`,
        },
      },
      cooldown: {
        description: `Manage cooldowns`,
        triggers: {
          description: `Set cooldown type and duration for triggers and /bot (defaults: off, 5s).`,
          cooldown_type_description: `How cooldowns apply (default: off; per-user, per-channel, server-wide).`,
          cooldown_length_description: `Cooldown duration in seconds (1-86400, default: 5).`,
          invalid_type_title: `Invalid Cooldown Type`,
          invalid_type_description: `The selected cooldown type is invalid. Please choose a valid option.`,
          invalid_length_title: `Invalid Duration`,
          invalid_length_description: `Duration must be between {min} and {max} seconds (24 hours).`,
          already_set_title: `Already Set`,
          already_set_description: `Cooldown settings are already **{type}** with **{length}** seconds.`,
          success_title: `Cooldown Updated`,
          success_description: `Cooldown updated from **{previous_type}**, **{previous_length}** seconds to **{type}**, **{length}** seconds. This applies to both message triggers and \`/bot\` commands.`,
          success_disabled_title: `Cooldowns Disabled`,
          success_disabled_description: `Cooldown updated from **{previous_type}**, **{previous_length}** seconds to **{type}**, **{length}** seconds. Message trigger and \`/bot\` command cooldowns are now disabled.`,
          type: {
            choice_off: `Off`,
            choice_per_user: `Per-User`,
            choice_per_channel: `Per-Channel`,
            choice_server_wide: `Server-Wide`,
            choice_strict_server_wide: `Strict Server-Wide`,
          },
        },
      },
      quota: {
        description: `Manage generation quotas`,
        imagegen: {
          description: `Configure daily image generation quotas for this server.`,
          unlimited: `Unlimited`,
          daily_user_quota_description: `Set the daily image generation limit per user.`,
          daily_user_quota_limit_description: `Daily images per user (0=unlimited, 1-100, default: 10).`,
          daily_user_quota_success_title: `User Quota Updated`,
          daily_user_quota_success_description: `Daily user quota set to **{limit}** images per day.`,
          serverwide_quota_description: `Set the total server-wide image generation limit.`,
          serverwide_quota_limit_description: `Total server images (0=unlimited, 1-99999, default: 0).`,
          serverwide_quota_success_title: `Server-wide Quota Updated`,
          serverwide_quota_success_description: `Server-wide quota set to **{limit}** images per period.`,
          serverwide_quota_resets_in_description: `Set how many days before server-wide quota resets.`,
          serverwide_quota_resets_in_days_description: `Days before reset (1-365, default: 365).`,
          serverwide_quota_resets_in_success_title: `Quota Reset Period Updated`,
          serverwide_quota_resets_in_success_description: `Server-wide quota will now reset every **{days}** days.`,
        },
        textgen: {
          description: `Configure text generation trigger quotas for this server.`,
          unlimited: `Unlimited`,
          daily_user_quota_description: `Set the daily text generation trigger limit per user.`,
          daily_user_quota_limit_description: `Daily text triggers per user (0=unlimited, 1-100, default: 0).`,
          daily_user_quota_success_title: `User Quota Updated`,
          daily_user_quota_success_description: `Daily user quota set to **{limit}** text trigger(s) per day.`,
          serverwide_quota_description: `Set the total server-wide text generation trigger limit.`,
          serverwide_quota_limit_description: `Total server text triggers (0=unlimited, 1-99999, default: 0).`,
          serverwide_quota_success_title: `Server-wide Quota Updated`,
          serverwide_quota_success_description: `Server-wide quota set to **{limit}** text trigger(s) per period.`,
          serverwide_quota_resets_in_description: `Set how many days before server-wide text quota resets.`,
          serverwide_quota_resets_in_days_description: `Days before reset (1-365, default: 365).`,
          serverwide_quota_resets_in_success_title: `Quota Reset Period Updated`,
          serverwide_quota_resets_in_success_description: `Server-wide text quota will now reset every **{days}** days.`,
        },
        reset: {
          description: `Reset a quota pool for image/text generation.`,
          scope_description: `Choose whether to reset a user's daily quota or the server-wide quota.`,
          scope_choice_user: `User`,
          scope_choice_server: `Server`,
          quota_type_description: `Choose which quota pool type to reset.`,
          quota_type_choice_imagegen: `Image Generation`,
          quota_type_choice_textgen: `Text Generation`,
          user_select_title: `Select a User`,
          user_select_description: `Pick a user whose daily quota should be reset.`,
          user_select_placeholder: `Select a user...`,
          success_title: `Quota Reset`,
          success_user_imagegen_description: `Reset daily image generation quota usage for {user}.`,
          success_user_textgen_description: `Reset daily text generation trigger quota usage for {user}.`,
          success_server_imagegen_description: `Reset the server-wide image generation quota pool.`,
          success_server_textgen_description: `Reset the server-wide text generation trigger quota pool.`,
        },
      },
      memberpermissions: {
        description: `Configure what non-admin members can teach me.`,
        option_description: `The type of memory members can teach.`,
        servermemories_option: `Server Memories`,
        attributelist_option: `Attribute List`,
        sampledialogues_option: `Sample Dialogues`,
        permission_choice_servermemories: `Server Memories`,
        permission_choice_attributelist: `Attribute List`,
        permission_choice_sampledialogues: `Sample Dialogues`,
        // Short descriptions shown in the select menu dropdown
        servermemories_desc: "Add/remove server-wide memories",
        attributelist_desc: "Add/remove personality attributes",
        sampledialogues_desc: "Add/remove sample dialogue pairs",
        // Checkbox select menu UI strings
        select_placeholder: "Select what members can teach...",
        select_embed_title: "Member Teaching Permissions",
        select_embed_description:
          "Select which things non-admin members can **teach** me. Checked = allowed.",
        no_changes_title: "No Changes Made",
        no_changes_description:
          "All permissions are already at the selected values.",
        timed_out_title: "Selection Timed Out",
        timed_out_description:
          "The permission menu timed out. No changes were applied.",
        set_description: `Enable or disable this permission for members.`,
        success_title: `Member Permissions Updated`,
        success_description: `Updated **{count}** permission(s)\n`,
        enabled_success: `Members can now teach: \`{permission_type}\`.`,
        disabled_success: `Members can no longer teach: \`{permission_type}\`.`,
        already_set_title: `Permission Already Set`,
        already_enabled_description: `Members are already allowed to teach \`{permission_type}\`.`,
        already_disabled_description: `Members are already prevented from teaching \`{permission_type}\`.`,
      },
      avatar: {
        description: `Set or remove avatar for a selected persona on this server.`,
        image_description: `Image to set as avatar (leave empty to remove the selected persona avatar).`,
        persona_modal_title: `Select Persona`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona avatar to update.`,
        persona_select_placeholder: `Select a persona...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        success_title: `Avatar Updated`,
        success_description: `Successfully updated my avatar for this server.`,
        success_alter_description: `Successfully updated avatar for persona "{persona_name}".`,
        removed_title: `Avatar Reset`,
        removed_description: `Successfully reset my avatar to the default for this server.`,
        removed_alter_description: `Successfully reset avatar for persona "{persona_name}".`,
        invalid_image_title: `Invalid Image`,
        invalid_image_description: `Please provide a valid image file.`,
        file_too_large_title: `File Too Large`,
        file_too_large_description: `The image file is too large. Maximum file size is 8MB.`,
        invalid_format_title: `Invalid Format`,
        invalid_format_description: `Please provide a PNG, JPG, JPEG, or GIF image file.`,
        conversion_error_title: `Conversion Error`,
        conversion_error_description: `Failed to process the image. Please try a different image file.`,
        api_error_title: `API Error`,
        api_error_description: `Failed to update the avatar through Discord's API. This is often caused by changing avatars too quickly (rate limits). Please wait and try again.`,

        error_download_timeout: `Avatar download timed out after 15 seconds. Please try again.`,
        error_api_timeout: `Discord API call timed out after 15 seconds. Please try again.`,
      },
      // Initialize subcommand group
      initialize: {
        description: `Initialize server features with AI analysis`,
        expressions: {
          description: `Analyze and classify all custom emojis and stickers using AI vision`,
          // Success messages
          success_title: `Expressions Initialized`,
          success_description: `Successfully analyzed and classified {emoji_count} emojis and {sticker_count} stickers ({total} total).`,
          // Error messages
          model_incompatible_title: `Incompatible Model`,
          model_incompatible_description: `Your current model ({model_name}) does not support {missing_capability}. Please switch to a model with both IMAGE VISION and STRUCTURED OUTPUT capabilities using \`/config model text\`.`,
          already_initialized_title: `Nothing to Initialize`,
          already_initialized_description: `All emojis and stickers have already been analyzed and classified.`,
          partial_success_title: `Partially Successful`,
          partial_success_description: `Analyzed {successful} of {total} expressions. {failed} expressions were not processed. Please re-run this command to process the remaining expressions.`,
          no_matches_title: `No Matches Found`,
          no_matches_description: `The AI analyzed the expressions but could not match any results to the database. This may be due to a processing error.`,
          llm_error_title: `AI Analysis Failed`,
          llm_error_description: `The AI model encountered an error while analyzing expressions. Please try again later.`,
          validation_error_title: `Invalid AI Response`,
          validation_error_description: `The AI returned an invalid response format. This may be a model issue.`,
          // Progress messages
          progress_fetching: `Fetching uninitialized expressions...`,
          progress_building: `Found {emoji_count} emojis and {sticker_count} stickers to analyze...`,
          progress_analyzing: `Analyzing {total} images...`,
          progress_analyzing_batch: `Analyzing {batch_size} of {total_uninitialized} images (processing in batches, please re-run this command to process remaining expressions)`,
          progress_analyzing_gemini_batch: `Analyzing {batch_size} of {total_uninitialized} images (Gemini processes in batches, please re-run this command after to process remaining expressions)`,
          progress_saving: `Saving results to database...`,
        },
      },
      // Matrix bridge management
      matrix: {
        link: {
          description: `Link a Discord channel to a Matrix room for bidirectional relay`,
          channel_description: `The Discord channel to link`,
          room_description: `The Matrix room ID to link (e.g., !abc:matrix.org)`,
          success_title: `Matrix Room Linked`,
          success_description: `<#{channel_id}> is now bridged to \`{room_id}\`. Messages from TomoriBot will appear in the Matrix room, and Matrix messages will appear here.

Use {help_matrix} for setup steps, Matrix-only command notes, and the current limitation list.`,
          invalid_room_title: `Invalid Room ID`,
          invalid_room_description: `The Matrix room ID must start with \`!\` and contain a \`:\` (e.g., \`!abc:matrix.org\`). Please check the room ID and try again.`,
          join_failed_description: `<#{channel_id}> has been linked to \`{room_id}\`, but I couldn't join the Matrix room automatically. Please invite \`{bot_user_id}\` to the room manually, then use {help_matrix} if you need the setup steps and limitation list.`,
          encrypted_room_title: `Cannot Link Encrypted Room`,
          encrypted_room_description: `\`{room_id}\` has end-to-end encryption enabled. Matrix encryption cannot be disabled once set, so this room cannot be used for bridging. Please create a new Matrix room **without** encryption and invite \`{bot_user_id}\` to it instead.`,
          matrix_not_configured_title: `Matrix Bridge Not Available`,
          matrix_not_configured_description: `The Matrix bridge is not configured on this bot instance. Contact the bot owner to enable it.`,
        },
        unlink: {
          description: `Remove the Matrix bridge link from a Discord channel`,
          channel_description: `The Discord channel to unlink from its Matrix room`,
          success_title: `Matrix Room Unlinked`,
          success_description: `<#{channel_id}> is no longer bridged to any Matrix room.`,
          not_linked_title: `Not Linked`,
          not_linked_description: `<#{channel_id}> doesn't have a Matrix room linked to it.`,
        },
      },
      alwaysreply: {
        description: `Toggle always-reply mode for the main persona.`,
        enabled_title: `Always-Reply Enabled`,
        enabled_description: `**{persona_name}** will now reply to all messages in this server, even without a trigger word. Alter personas still require their trigger words. If an alter is triggered, **{persona_name}** will stay quiet to avoid doubling up.`,
        disabled_title: `Always-Reply Disabled`,
        disabled_description: `**{persona_name}** will now only reply when triggered by a trigger word, mention, or reply.`,
      },
    },

    // Personal user configuration commands
    personal: {
      description: `Manage your personal settings`,
      privacy: {
        description: `Control personal memory storage and privacy settings`,

        // Modal UI
        modal_title: `Privacy Settings`,
        select_label: `Privacy Level`,
        select_description: `Choose how much privacy protection you want`,
        select_placeholder: `Select privacy level...`,

        // Level 0 (MINIMAL privacy - full features)
        choice_minimal: `None`,
        desc_minimal: `Full personalization: memories, status, custom nickname, can trigger bot.`,

        // Level 1 (PARTIAL privacy)
        choice_partial: `Partial`,
        desc_partial: `Messages visible but no personal memories/status shown to AI.`,

        // Level 2 (FULL privacy - maximum protection)
        choice_full: `Full`,
        desc_full: `Maximum privacy: completely invisible, no messages, memories, or bot triggering.`,

        // Success/error messages
        success_title: `Privacy Settings Updated`,
        success_description: `Your privacy level has been changed from \`{previous_value}\` to \`{value}\`.

You can change this anytime using \`/personal privacy\`.`,

        already_set_title: `No Changes Made`,
        already_set_description: `Your privacy level is already set to \`{value}\`.`,

        invalid_value_description: `Invalid privacy level selected. Please try again.`,
      },

      language: {
        description: `Set your preferred language for my interface.`,
        value_description: `Choose your preferred language for interfaces.`,
        choice_english: `English`,
        choice_japanese: `Japanese`,
        "value_choice_en-US": `English`,
        value_choice_ja: `Japanese`,
        invalid_value_title: `Invalid Language`,
        invalid_value_description: `Language must be one of: {supported}.`,
        already_set_title: `Language Already Set`,
        already_set_description: `Your language preference is already set to \`{value}\`.`,
        success_title: `Language Updated`,
        success_description: `Your interface language changed from \`{previous_value}\` to \`{value}\`.`,
      },

      nickname: {
        description: `Change the name I use to refer to you.`,
        option_description: `The nickname I should use for you (2-32 characters).`,
        invalid_length_title: `Invalid Nickname Length`,
        invalid_length: `Nickname must be between {min} and {max} characters.`,
        success_title: `Personal Nickname Updated`,
        success_description: `I'll call you '{new_nickname}' from now on! (previously '{old_nickname}').`,
        success_but_disabled_description: `I'll remember to call you '{new_nickname}'! (previously '{old_nickname}').

**Warning:** Personalization is currently disabled on this server, so I won't use this nickname here. I'll still use it on other servers where personalization is enabled.`, // Natural line break
      },

      impersonate: {
        description: `Manage user impersonation settings.`,
        prompt: {
          description: `Set a reusable prompt for user impersonation replies.`,
          modal_title: `User Impersonation Prompt`,
          prompt_label: `Persona Prompt`,
          prompt_description: `Used whenever your user impersonation is invoked. Leave blank to clear it.`,
          prompt_placeholder: `Write casually, keep it short, use lots of lowercase, tease friends a little...`,
          success_title: `Impersonation Prompt Updated`,
          success_description: `Your user impersonation prompt will now be used for future user impersonation replies everywhere.`,
          cleared_title: `Impersonation Prompt Cleared`,
          cleared_description: `Your user impersonation prompt has been cleared.`,
          already_set_title: `No Changes Made`,
          already_set_description: `Your user impersonation prompt is already set to that value.`,
          already_cleared_title: `No Prompt Set`,
          already_cleared_description: `You don't currently have a user impersonation prompt set.`,
        },
      },

      stm: {
        description: `Configure STM (short-term memory) settings`,
        option_description: `Which STM setting to configure`,
        crossserver_option: `Cross-server STM sharing`,
        clear_option: `Clear personal STM`,
        crossserver: {
          title: `Cross-Server STM Sharing`,
          enabled: `Cross-server STM sharing is now **enabled**. I can now reference your conversations from other servers when talking to you.`,
          disabled: `Cross-server STM sharing is now **disabled**. I will only reference your conversations from this server.`,
        },
        clear: {
          title: `STM Cleared`,
          success: `Your user-specific STM has been cleared across all channels.`,
        },
      },
    },

    // Commands for teaching Tomori
    teach: {
      sampledialogue: {
        description: `Add a sample user/bot dialogue pair to as an example for how I should respond.`,
        teaching_disabled_title: `Sample Dialogue Teaching Disabled`,
        teaching_disabled_description: `Members are currently not allowed to teach/forget sample dialogues on this server. A server member with \`Manage Server\` permissions can enable this using \`/server memberpermissions\`.`,
        modal_title: `Add Sample Dialogue`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona this dialogue is for.`,
        persona_select_placeholder: `Select a persona...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        user_input_label: `User's Line`,
        user_input_description: `Optional single user line. Leave blank when importing from .txt.`,
        user_input_placeholder: `What's your favorite food?`,
        bot_input_label: `My Response`,
        bot_input_description: `Optional single bot line. Leave blank when importing from .txt.`,
        bot_input_placeholder: `I-I like mango floats...`,
        batch_file_label: `Batch .txt File`,
        batch_file_description: `Optional: line1 {user}:/{{user}}:, line2 {bot}:/{{char}}:, repeat per pair.`,
        no_input_title: `No Input Provided`,
        no_input_description: `Enter both manual lines or upload a .txt file.`,
        manual_pair_required_description: `Manual entry needs both User's Line and My Response.`,
        invalid_file_title: `Invalid File`,
        invalid_file_description: `Upload a .txt file for batch dialogue import.`,
        file_too_large_description: `The .txt file is too large. Maximum file size is {max_size} MB.`,
        download_failed_description: `Couldn't download the uploaded file. Please try again.`,
        invalid_batch_format_title: `Invalid Batch Format`,
        invalid_batch_format_description: `Line {line_number} is invalid. Expected prefix: {expected_prefix}`,
        duplicate_title: `No New Dialogues`,
        duplicate_description: `All provided dialogue pairs already exist.`,
        limit_exceeded_title: `Sample Dialogue Limit Exceeded`,
        limit_exceeded_description: `This server has reached its sample dialogue limit of {max_allowed} dialogues (currently has {current_count}). Please remove some sample dialogues with \`/forget sampledialogue\` before adding new ones.`,
        batch_limit_exceeded_title: `Batch Import Exceeds Limit`,
        batch_limit_exceeded_description: `Import needs {import_count} slots, but only {max_allowed} total ({current_count} used). Remove {remove_count} sample dialogues and try again.`,
        user_input_too_long_title: `User Input Too Long`,
        user_input_too_long_description: `The user input is too long ({current_length} characters). Maximum allowed length is {max_allowed} characters.`,
        bot_input_too_long_title: `Bot Response Too Long`,
        bot_input_too_long_description: `The bot response is too long ({current_length} characters). Maximum allowed length is {max_allowed} characters.`,
        success_title: `Sample Dialogue Added`,
        success_description: `Successfully added a new sample dialogue pair:

**User:**
> {user_input}

**Me:**
> {bot_input}`, // Natural line breaks here
        batch_success_title: `Sample Dialogues Added`,
        batch_success_description: `Added {added_count} sample dialogue pairs.`,
      },
      attribute: {
        description: `Add a personality attribute describing me for this server.`,
        teaching_disabled_title: `Attribute Teaching Disabled`,
        teaching_disabled_description: `Members are not currently allowed to teach/forget personality attributes on this server. A server member with \`Manage Server\` permissions can enable this using \`/server memberpermissions\`.`,
        modal_title: `Add Personality Attribute`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona this attribute is for.`,
        persona_select_placeholder: `Select a persona...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        modal_description: `A personality trait that I have for this server. Use \`{bot}\` as a placeholder for my name`,
        attribute_input_label: `New Attribute`,
        attribute_input_description: `Optional single attribute. Leave blank when importing from .txt.`,
        attribute_input_placeholder: `{bot} likes mango floats`,
        batch_file_label: `Batch .txt File`,
        batch_file_description: `Optional: one attribute per non-empty line.`,
        no_input_title: `No Input Provided`,
        no_input_description: `Enter an attribute or upload a .txt file.`,
        invalid_file_title: `Invalid File`,
        invalid_file_description: `Upload a .txt file for batch attribute import.`,
        file_too_large_description: `The .txt file is too large. Maximum file size is {max_size} MB.`,
        download_failed_description: `Couldn't download the uploaded file. Please try again.`,
        duplicate_title: `Duplicate Attribute`,
        duplicate_description: `This attribute '{attribute}' is already in my attribute list.`,
        limit_exceeded_title: `Attribute Limit Exceeded`,
        limit_exceeded_description: `This server has reached its attribute limit of {max_allowed} attributes (currently has {current_count}). Please remove some attributes with \`/forget attribute\` before adding new ones.`,
        batch_limit_exceeded_title: `Batch Import Exceeds Limit`,
        batch_limit_exceeded_description: `Import needs {import_count} slots, but only {max_allowed} total ({current_count} used). Remove {remove_count} attributes and try again.`,
        content_too_long_title: `Attribute Content Too Long`,
        content_too_long_description: `The attribute content is too long ({current_length} characters). Maximum allowed length is {max_allowed} characters.`,
        success_title: `Attribute Added`,
        success_description: `Successfully added '{attribute}' to my personality attributes.`,
        batch_success_title: `Attributes Added`,
        batch_success_description: `Added {added_count} attributes to my personality.`,
      },
      document: {
        description: `Upload a document for me to reference using Retrieval-Augmented Generation.`,
        scope_description: `Choose whether this document is persona-only (default) or shared server-wide.`,
        scope_choice_persona: `Persona`,
        scope_choice_serverwide: `Serverwide`,
        persona_modal_title: `Select Persona`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona this document is for.`,
        persona_select_placeholder: `Select a persona...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        persona_description: `Target persona nickname when scope is Persona (defaults to main persona).`,
        name_description: `Name this document (must be unique within the selected scope).`,
        file_description: `Upload a document file (.txt, .md, .pdf).`,
        rag_disabled_title: `Document RAG Disabled`,
        rag_disabled_description: `Document retrieval is disabled by default in local instances. Set \`ACTIVATE_LOCAL_RAG=true\` in .env to enable it locally.`,
        teaching_disabled_title: `Document Teaching Disabled`,
        teaching_disabled_description: `Members are not currently allowed to teach/forget documents on this server. A server member with \`Manage Server\` permissions can enable this using \`/server memberpermissions\`.`,
        no_embedding_model_title: `No Embedding Model Set`,
        no_embedding_model_description: `An embedding model is not configured for this provider. Please set one using \`/config model embedding\`.`,
        no_api_key_title: `No API Key Set`,
        no_api_key_description: `An API key is required to embed documents. Please use \`/config apikey set\`.`,
        invalid_name_title: `Invalid Document Name`,
        invalid_name_description: `Please provide a valid document name (1-64 characters).`,
        duplicate_title: `Document Name Already Exists`,
        duplicate_description: `A document named \`{name}\` already exists. Please choose a different name.`,
        limit_exceeded_title: `Document Limit Reached`,
        limit_exceeded_description: `This scope ({scope}) already has {current_count} documents (max {max_allowed}). Remove some with \`/forget document\` before adding new ones.`,
        invalid_file_title: `Invalid File`,
        invalid_format: `Please upload a .txt, .md, or .pdf file.`,
        file_too_large_title: `File Too Large`,
        file_too_large_description: `Maximum file size is {max_size} MB.`,
        download_failed_title: `Download Failed`,
        download_failed_description: `Failed to download the uploaded file. Please try again.`,
        empty_title: `Document Empty`,
        empty_description: `The document didn't contain any readable text.`,
        too_long_title: `Document Too Long`,
        too_long_description: `Document text is too long. Maximum length is {max_length} characters.`,
        too_many_chunks_title: `Too Many Chunks`,
        too_many_chunks_description: `Document is too large after chunking. Maximum chunks per document is {max_chunks}.`,
        server_chunk_limit_title: `Server Chunk Limit Reached`,
        server_chunk_limit_description: `This scope ({scope}) would exceed the chunk limit of {max_chunks}. Remove some documents first.`,
        success_title: `Document Added`,
        success_description: `Stored **{name}** with {chunk_count} chunks for {scope}.`,
        persona_scope_mismatch: `The persona option can only be used when scope is set to Persona.`,
        scope_label_persona: `persona "{persona_name}"`,
        scope_label_serverwide: `serverwide scope`,
      },
      history: {
        description: `Extract knowledge from this channel's message history using AI.`,
        name_description: `Name for the generated document (must be unique within the selected scope).`,
        scope_description: `Choose knowledge scope: persona (default), automatic (detect personas), or global.`,
        scope_choice_persona: `Persona`,
        scope_choice_automatic: `Automatic`,
        scope_choice_global: `Global`,
        rag_disabled_title: `Document RAG Disabled`,
        rag_disabled_description: `Document retrieval is disabled by default in local instances. Set \`ACTIVATE_LOCAL_RAG=true\` in .env to enable it locally.`,
        no_permission_title: `Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to extract channel history.`,
        model_incompatible_title: `Model Incompatible`,
        model_incompatible_description: `The current model does not support structured output, which is required for history extraction. Please switch to a compatible model using \`/config model text\`.`,
        no_embedding_model_title: `No Embedding Model Set`,
        no_embedding_model_description: `An embedding model is not configured. Please set one using \`/config model embedding\`.`,
        no_api_key_title: `No API Key Set`,
        no_api_key_description: `An API key is required to extract and embed history. Please use \`/config apikey set\`.`,
        no_messages_title: `No Messages Found`,
        no_messages_description: `No messages were found in this channel to extract knowledge from.`,
        no_facts_extracted_title: `No Facts Extracted`,
        no_facts_extracted_description: `The AI could not extract any meaningful facts from the channel history. This can happen if the conversation is too short or consists only of trivial messages.`,
        duplicate_title: `Document Name Already Exists`,
        duplicate_description: `A document named \`{name}\` already exists in this scope. Please choose a different name.`,
        limit_exceeded_title: `Document Limit Reached`,
        limit_exceeded_description: `This scope ({scope}) already has {current_count} documents (max {max_allowed}). Remove some with \`/forget document\` or \`/forget history\` before adding new ones.`,
        server_chunk_limit_title: `Server Chunk Limit Reached`,
        server_chunk_limit_description: `This scope ({scope}) would exceed the chunk limit of {max_chunks}. Remove some documents first.`,
        progress_fetching: `Fetching channel messages...`,
        progress_extracting: `Extracting knowledge from {message_count} messages (window {current}/{total})...`,
        progress_embedding: `Generating embeddings for {fact_count} facts...`,
        success_title: `History Extracted`,
        success_description: `Extracted **{fact_count}** facts from **{message_count}** messages and stored as **{name}** ({chunk_count} chunks) for {scope}.`,
        success_automatic_description: `Extracted **{fact_count}** facts from **{message_count}** messages.\n\n{persona_list}`,
        success_automatic_persona_line: `**{persona_name}**: stored as **{doc_name}** ({chunk_count} chunks)`,
        success_automatic_global_fallback: `No personas detected. Stored as **{name}** for serverwide scope.`,
        scope_label_persona: `persona "{persona_name}"`,
        scope_label_global: `serverwide scope`,
      },
      personaprompt: {
        description: `Set a persona-specific prompt appended after sysprompt`,
        no_permission_title: `🔴 Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to set persona prompts.`,
        persona_select_label: `Persona`,
        persona_select_description: `Choose which persona to update.`,
        persona_select_placeholder: `Select a persona...`,
        main_persona_description: `Main Persona`,
        alter_persona_description: `Alter Persona`,
        modal_title: `Set Persona Prompt`,
        prompt_label: `Persona Prompt`,
        prompt_description: `This is appended after the system prompt for this persona.`,
        prompt_placeholder: `Example: Speak like a veteran tactician, concise and calm.`,
        success_title: `Persona Prompt Updated`,
        success_description: `Updated persona prompt for "{persona_name}".`,
      },
      memory: {
        description: `Manage my memories`,
        personal: {
          description: `Add a personal memory of you I can remember across any server.`,
          scope_description: `Memory scope: persona-only (default) or global across all personas/servers`,
          scope_choice_persona: `Persona memories (default)`,
          scope_choice_global: `Global memories (all personas/servers)`,
          modal_title: `Add Personal Memory`,
          persona_select_label: `Persona`,
          persona_select_description: `Choose which persona this memory is for.`,
          persona_select_placeholder: `Select a persona...`,
          main_persona_description: `Main Persona`,
          alter_persona_description: `Alter Persona`,
          modal_description: `A memory of you that I remember no matter the server.`,
          memory_input_label: `New Personal Memory`,
          memory_input_description: `Optional single memory. Leave blank when importing from .txt.`,
          memory_input_placeholder: `{user} likes mango floats`,
          batch_file_label: `Batch .txt File`,
          batch_file_description: `Optional: one memory per non-empty line.`,
          no_input_title: `No Input Provided`,
          no_input_description: `Enter a memory or upload a .txt file.`,
          invalid_file_title: `Invalid File`,
          invalid_file_description: `Upload a .txt file for batch memory import.`,
          file_too_large_description: `The .txt file is too large. Maximum file size is {max_size} MB.`,
          download_failed_description: `Couldn't download the uploaded file. Please try again.`,
          duplicate_title: `Duplicate Personal Memory`,
          duplicate_description: `This memory '{memory}' is already in your personal memories.`,
          limit_exceeded_title: `Personal Memory Limit Reached`,
          limit_exceeded_description: `You have reached your personal memory limit of {max_allowed} memories (currently have {current_count}). Please remove some memories with \`/forget memory personal\` before adding new ones.`,
          batch_limit_exceeded_title: `Batch Import Exceeds Limit`,
          batch_limit_exceeded_description: `Import needs {import_count} slots, but only {max_allowed} total ({current_count} used). Remove {remove_count} memories and try again.`,
          content_too_long_title: `Memory Content Too Long`,
          content_too_long_description: `The memory content is too long. Maximum allowed length is {max_length} characters.`,
          success_title: `Personal Memory Added`,
          success_description: `Successfully added '{memory}' to your personal memories.`,
          batch_success_title: `Personal Memories Added`,
          batch_success_description: `Successfully added {added_count} memories to your personal memories.`,
          success_but_disabled_description: `Successfully added '{memory}' to your personal memories.

**Warning:** Personalization is currently disabled on this server, so this memory won't be used here. It will still be available on other servers where personalization is enabled.`, // Natural line break
          batch_success_but_disabled_description: `Successfully added {added_count} memories to your personal memories.

**Warning:** Personalization is currently disabled on this server, so these memories won't be used here. They will still be available on other servers where personalization is enabled.`,
          success_but_blacklisted_description: `Successfully added '{memory}' to your personal memories.

**Warning:** You are currently blacklisted from personalization features on this server, so this memory won't be used here. It will still be available on other servers where you are not blacklisted.`, // Natural line break
          batch_success_but_blacklisted_description: `Successfully added {added_count} memories to your personal memories.

**Warning:** You are currently blacklisted from personalization features on this server, so these memories won't be used here. They will still be available on other servers where you are not blacklisted.`,
          opted_out_error_title: `Privacy Protection Active`,
          opted_out_error_description: `You have opted out of personal memory storage for privacy reasons. If you'd like to allow personal memories again, use \`/personal privacy\` to opt back in.`,
        },
        server: {
          description: `Add a server memory to my knowledge base.`,
          teaching_disabled_title: `Server Memory Teaching Disabled`,
          teaching_disabled_description: `Members are not currently allowed to add/remove server memories on this server. A server member with \`Manage Server\` permissions can enable this using \`/server memberpermissions\`.`,
          modal_title: `Add Server Memory`,
          persona_select_label: `Persona`,
          persona_select_description: `Choose which persona this server memory is for.`,
          persona_select_placeholder: `Select a persona...`,
          main_persona_description: `Main Persona`,
          alter_persona_description: `Alter Persona`,
          modal_description: `A memory that I remember for this server only.`,
          memory_input_label: `New Server Memory`,
          memory_input_description: `Optional single memory. Leave blank when importing from .txt.`,
          memory_input_placeholder: `This server's members like mango floats`,
          batch_file_label: `Batch .txt File`,
          batch_file_description: `Optional: one memory per non-empty line.`,
          no_input_title: `No Input Provided`,
          no_input_description: `Enter a memory or upload a .txt file.`,
          invalid_file_title: `Invalid File`,
          invalid_file_description: `Upload a .txt file for batch memory import.`,
          file_too_large_description: `The .txt file is too large. Maximum file size is {max_size} MB.`,
          download_failed_description: `Couldn't download the uploaded file. Please try again.`,
          duplicate_title: `Duplicate Memory`,
          duplicate_description: `This memory '{memory}' is already in my memories for this server.`,
          limit_exceeded_title: `Server Memory Limit Reached`,
          limit_exceeded_description: `This server has reached its memory limit of {max_allowed} memories (currently has {current_count}). Please remove some memories with \`/forget memory server\` before adding new ones.`,
          batch_limit_exceeded_title: `Batch Import Exceeds Limit`,
          batch_limit_exceeded_description: `Import needs {import_count} slots, but only {max_allowed} total ({current_count} used). Remove {remove_count} memories and try again.`,
          content_too_long_title: `Memory Content Too Long`,
          content_too_long_description: `The memory content is too long. Maximum allowed length is {max_length} characters.`,
          success_title: `Server Memory Added`,
          success_description: `Successfully added '{memory}' to my server memories.`,
          batch_success_title: `Server Memories Added`,
          batch_success_description: `Added {added_count} memories to server memory.`,
        },
      },
    },

    // Commands for making Tomori forget things
    forget: {
      sampledialogue: {
        description: `Remove a sample user/bot dialogue pair from my memory.`,
        modal_title: `Remove Sample Dialogue`,
        select_label: `Dialogue to Remove`,
        select_description: `Choose which dialogue pair to remove`,
        select_placeholder: `Select a dialogue...`,
        no_dialogues_title: `No Sample Dialogues`,
        no_dialogues: `There are no sample dialogues stored to remove. Add some with \`/teach sampledialogue\`.`,
        select_title: `Remove Sample Dialogue`,
        dialogue_label: `Dialogue Pair`,
        success_title: `Sample Dialogue Removed`,
        success_description: `Successfully removed the dialogue pair: User: "{input}" → Bot: "{output}"`,
      },
      attribute: {
        description: `Remove a personality attribute from my memory.`,
        modal_title: `Remove Attribute`,
        select_label: `Attribute to Remove`,
        select_description: `Choose which attribute to remove from my personality`,
        select_placeholder: `Select an attribute...`,
        no_attributes_title: `No Attributes`,
        no_attributes: `There are no personality attributes to remove. Add some with \`/teach attribute\`.`,
        select_title: `Remove Attribute`,
        attribute_label: `Attribute`,
        success_title: `Attribute Removed`,
        success_description: `Successfully removed the attribute: "{attribute}"`,
      },
      document: {
        description: `Remove a document from the server knowledge base.`,
        scope_description: `Choose whether to remove from a persona scope or serverwide scope.`,
        scope_choice_persona: `Persona`,
        scope_choice_serverwide: `Serverwide`,
        modal_title: `Remove Document`,
        select_label: `Document to Remove`,
        select_description: `Choose which document to remove`,
        select_placeholder: `Select a document...`,
        rag_disabled_title: `Document RAG Disabled`,
        rag_disabled_description: `Document retrieval is disabled by default in local instances. Set \`ACTIVATE_LOCAL_RAG=true\` in .env to enable it locally.`,
        none_title: `No Documents`,
        none_description: `There are no documents to remove in this scope. Add one with \`/teach document\`.`,
        success_title: `Document Removed`,
        success_description: `Successfully removed the document: "{name}"`,
      },
      history: {
        description: `Remove a history-extracted document from the server knowledge base.`,
        scope_description: `Choose whether to remove from a persona scope or serverwide scope.`,
        scope_choice_persona: `Persona`,
        scope_choice_serverwide: `Serverwide`,
        modal_title: `Remove History Document`,
        select_label: `Document to Remove`,
        select_description: `Choose which history document to remove`,
        select_placeholder: `Select a document...`,
        rag_disabled_title: `Document RAG Disabled`,
        rag_disabled_description: `Document retrieval is disabled by default in local instances. Set \`ACTIVATE_LOCAL_RAG=true\` in .env to enable it locally.`,
        none_title: `No History Documents`,
        none_description: `There are no history-extracted documents to remove in this scope. Extract some with \`/teach history\`.`,
        success_title: `History Document Removed`,
        success_description: `Successfully removed the history document: "{name}"`,
      },
      personaprompt: {
        description: `Clear a persona-specific prompt`,
        no_permission_title: `🔴 Permission Denied`,
        no_permission_description: `You need the **Manage Server** permission to clear persona prompts.`,
        success_title: `Persona Prompt Cleared`,
        success_description: `Cleared persona prompt for "{persona_name}".`,
      },
      reminder: {
        description: `Remove a reminder.`,
        modal_title: `Remove Reminder`,
        select_label: `Reminder to Remove`,
        select_description: `Choose which reminder to remove`,
        select_placeholder: `Select a reminder...`,
        no_reminders_title: `No Reminders`,
        no_reminders: `There are no reminders to remove. Set one by asking me to remind you.`,
        success_title: `Reminder Removed`,
        success_description: `Successfully removed the reminder: "{reminder_purpose}"`,
      },
      memory: {
        description: `Manage my memories`,
        personal: {
          description: `Remove a personal memory.`,
          scope_description: `Memory scope: persona-only (default) or global across all personas/servers`,
          scope_choice_persona: `Persona memories (default)`,
          scope_choice_global: `Global memories (all personas/servers)`,
          modal_title: `Remove Personal Memory`,
          select_label: `Memory to Remove`,
          select_description: `Choose which personal memory to remove`,
          select_placeholder: `Select a memory...`,
          no_memories_title: `No Personal Memories`,
          no_memories: `You don't have any personal memories stored. Add some with \`/teach memory personal\`.`,
          select_title: `Remove Personal Memory`,
          memory_label: `Personal Memory`,
          success_title: `Personal Memory Removed`,
          success_description: `Successfully removed the personal memory: "{memory}"`,
          warning_disabled_title: `Personalization Disabled`,
          warning_disabled_description: `The memory was successfully removed.

**Warning:** Personalization is currently disabled on this server, so this change won't affect my behavior here. It will still be reflected on other servers where personalization is enabled.`, // Natural line break
        },
        server: {
          description: `Remove a server memory from my knowledge.`,
          modal_title: `Remove Server Memory`,
          select_label: `Memory to Remove`,
          select_description: `Choose which server memory to remove`,
          select_placeholder: `Select a memory...`,
          no_memories_title: `No Server Memories`,
          no_memories: `There are no server memories stored for this server. Add some with \`/teach memory server\`.`,
          no_owned_memories: `You don't own any server memories that can be removed.`,
          memory_not_found: `The selected memory could not be found.`,
          select_title: `Remove Server Memory`,
          memory_label: `Server Memory`,
          success_title: `Server Memory Removed`,
          success_description: `Successfully removed the server memory: "{memory}"`,
        },
      },
    },

    generate: {
      image: {
        // Command
        description: "Generate an AI image using Google Gemini or OpenRouter",

        // Modal
        modal: {
          title: "Generate Image",
          prompt_label: "Image Prompt",
          prompt_description: "Describe the image you want to generate",
          prompt_placeholder:
            "A cute short-haired elven anime girl eating a banana, manga style",
          image_upload_label: "Reference Image (Optional)",
          image_upload_2_label: "Reference Image 2 (Optional)",
          image_upload_3_label: "Reference Image 3 (Optional)",
          image_upload_description:
            "Upload a reference image for image-to-image generation",
          aspect_ratio_label: "Aspect Ratio",
          aspect_ratio_description: "Select the desired aspect ratio",
          aspect_ratio_placeholder: "Choose aspect ratio...",
        },

        // Success embed
        success_title: "🟢 Image Generated Successfully!",
        success_description: "Your AI-generated image is ready!",
        field_prompt: "Prompt",
        field_model: "Model",
        field_generation_time: "Generation Time",
        field_aspect_ratio: "Aspect Ratio",

        // Provider-specific warnings
        zai_no_img2img_warning:
          "Z.ai does not support image-to-image generation. Your reference images were ignored, but the image will still be generated from your text prompt.",
        nvidia_no_img2img_warning:
          "NVIDIA NIM does not support image-to-image generation. Your reference images were ignored, but the image will still be generated from your text prompt.",

        // Errors
        disabled_title: "🔴 Image Generation Disabled",
        disabled_description:
          "Image generation is disabled on this server. A server member with `Manage Server` permissions can enable it using `/config permissions`.",
        wrong_provider_title: "🔴 Unsupported Provider",
        wrong_provider_description:
          "Image generation requires a provider with native image generation support. Your current provider is **{current_provider}**.",
        no_api_key_title: "🔴 No API Key",
        no_api_key_description:
          "No API key configured. Please use `/config apikey set`.",
        api_key_decrypt_failed_title: "🔴 API Key Error",
        api_key_decrypt_failed_description:
          "Failed to decrypt API key. Please reconfigure using `/config apikey set`.",
        no_diffusion_model_title: "🔴 No Image Model",
        no_diffusion_model_description:
          "No diffusion model configured for your provider.",
        error_billing_title: "🔴 Billing Required",
        error_billing_description:
          "Your API key requires billing to be enabled for image generation.",
        error_safety_title: "🔴 Content Blocked",
        error_safety_description:
          "Your prompt was blocked by safety filters. Please try a different prompt.",
        error_generation_failed_title: "🔴 Generation Failed",
        error_generation_failed_description:
          "Failed to generate image: {error}",
        invalid_image_title: "🔴 Invalid Image",
        invalid_image_description:
          "Please upload valid image files (PNG, JPG, etc.).",
        // Quota errors
        quota_exceeded_title: "🔴 Image Quota Exceeded",
        quota_exceeded_description:
          "You have reached your image generation quota. {reset_info}",
        user_quota_exceeded_description:
          "You have reached your daily image generation quota. {reset_info}",
        serverwide_quota_exceeded_description:
          "This server has reached its image generation quota for this period. {reset_info}",
        quota_resets_in_hours: "Quota resets in {hours} hour(s).",
        quota_resets_in_days: "Quota resets in {days} day(s).",
        quota_exceeded_footer:
          "This quota is configured by this server's managers via `/server quota`.",
      },
    },
  },

  events: {
    // Messages for when the bot is added to a server
    addBot: {
      rejoin_title: `TomoriBot is Back!`,
      rejoin_description: `Looks like I was re-added to this server. My previous settings and personality are still intact! You can manage me using the \`/config\`, \`/teach\`, and \`forget\` commands. You can also manage or delete your data anytime with \`/data\`.

			If you wish to swap my provider, use the \`/config apikey set\` command.

			**By using TomoriBot, you agree to these [Terms of Service](https://github.com/Bredrumb/TomoriBot/blob/main/legal/en-US/terms-of-service.md) and [Privacy Policy](https://github.com/Bredrumb/TomoriBot/blob/main/legal/en-US/privacy-policy.md).** View them anytime with \`/legal terms\` and \`/legal privacy\`.`,
      setup_prompt_title: `TomoriBot Successfully Added`,
      setup_prompt_description: `Thanks for adding me! To get started, someone with the **Manage Server** permission needs to run my \`/config setup\` command to choose my initial personality and configure my AI features. You can also manage or delete your data anytime with \`/data\`.

			Use the \`/help apikey\` command if you are unsure on how to create an API key for your chosen AI provider. API keys will be kept encrypted but if you are still wary of giving it to a public Discord bot, feel free to run your own TomoriBot using the [repository's guide](https://github.com/Bredrumb/TomoriBot) instead.

			**By using TomoriBot, you agree to these [Terms of Service](https://github.com/Bredrumb/TomoriBot/blob/main/legal/en-US/terms-of-service.md) and [Privacy Policy](https://github.com/Bredrumb/TomoriBot/blob/main/legal/en-US/privacy-policy.md).** View them anytime with \`/legal terms\` and \`/legal privacy\`.`,
    },
  },

  // Reminder system messages
  reminders: {
    // Confirmation embed when reminder is set
    reminder_set_title: `⏰ {persona_nickname} Set a Reminder`,
    reminder_set_description: `I'll remind {user_nickname} about "**{reminder_purpose}**" at \`{reminder_time}\``,
    reminder_set_footer: `A mention will be sent after {time_remaining} from now. Delete reminders with \`/forget reminder\`.`,
    reminder_set_footer_recurring: `First mention in {time_remaining}. Repeats every {repetition_interval_hours} hour(s). Delete reminders with \`/forget reminder\`.`,

    // Recurring task setup (self reminders)
    recurring_task_set_title: `🔁 {persona_nickname} Set Up a Recurring Task`,
    recurring_task_set_description: `I'll run "**{reminder_purpose}**" starting at \`{reminder_time}\`, then repeat every {repetition_interval_hours} hour(s).`,
    recurring_task_set_footer: `You can delete reminders using \`/forget reminder\`.`,

    // One-time task setup (self reminders, non-recurring)
    task_set_title: `✅ {persona_nickname} Set Up a Task`,
    task_set_description: `I'll execute "**{reminder_purpose}**" at \`{reminder_time}\``,
    task_set_footer: `The task will run in {time_remaining}. Delete reminders with \`/forget reminder\`.`,

    // Fallback info embed when AI generation fails - shows the raw reminder/task content
    reminder_triggered_title: `🔵 Reminder Triggered`,
    task_triggered_title: `🔵 Task Triggered`,
    triggered_description: `{reminder_purpose}`,
    triggered_footer: `An error occurred during generation, so the raw reminder has been sent instead`,
  },

  // Tool messages
  tools: {
    generate_image: {
      // Quota error messages
      quota_exceeded_generic: `Image generation quota has been exceeded.`,
      user_quota_exceeded: `You have reached your daily image generation quota. {reset_info}`,
      serverwide_quota_exceeded: `This server has reached its image generation quota for this period. {reset_info}`,
      quota_resets_in_hours: `Quota resets in {hours} hour(s).`,
      quota_resets_in_days: `Quota resets in {days} day(s).`,
      quota_remaining: `You have {remaining} image(s) remaining for today.`,
    },
    generate_image_nai: {
      no_google_api_key: `Inpainting requires a Google API key for image segmentation. Set one with /optionalkey google set, or switch to the Google provider.`,
      provider_quota_exceeded: `NovelAI image generation quota is exhausted for this account. Recharge Anlas or wait for the quota to refresh, then try again.`,
      characters_require_v4: `Character positioning requires a NovelAI V4 diffusion model or newer.`,
      character_requires_id_or_tags: `Character entry #{index} must include either an id or tags.`,
      invalid_character_identity: `Invalid character identity: {id}. Use persona:<id>, a short numeric persona ID, or a Discord user snowflake.`,
    },
  },

  // Matrix bridge - concise summaries of Discord embeds relayed to Matrix rooms.
  // Discord embeds cannot be rendered natively in Matrix, so tool-result embeds are
  // converted to short bracketed notices that convey the key information inline.
  matrix: {
    embed: {
      server_memory_learned: `[🧠 I learned "{memory}"]`,
      personal_memory_learned: `[💡 I learned something personal: "{memory}"]`,
      server_memory_updated: `[📝 I updated a memory: "{memory}"]`,
      personal_memory_updated: `[📝 I updated a personal memory: "{memory}"]`,
      reminder_set: `[⏰ {description}]`,
      task_set: `[✅ {description}]`,
      recurring_task_set: `[🔁 {description}]`,
    },
    notices: {
      invited: `TomoriBot joined this room.

To finish setup:
1. In Discord, run {link_command} in the channel you want to bridge.
2. Paste this room's Internal Room ID from {room_id_path}.

Important:
- This room must stay unencrypted.
- Once linked, you can talk here normally.
- The only Matrix text commands are {kill_command} and {refresh_command}.

Use {help_command} in Discord for the full guide and limitation list.`,
      linked: `This room is now bridged to the Discord channel {channel_name}.

Quick tips:
- Chat here normally to talk to TomoriBot.
- The only Matrix text commands are {kill_command} and {refresh_command}.
- Slash commands, DMs, and pinning are not available from Matrix.
- Custom emojis/Markdown do not render reliably, and embeds relay as plain text.
- Personal memories for Matrix users fall back to server memories.

Use {help_command} in Discord for the full guide and current limitations.`,
    },
  },
};
