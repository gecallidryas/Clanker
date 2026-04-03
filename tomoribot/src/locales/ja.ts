// locales/ja.ts

// ロケール構造全体をデフォルトオブジェクトとしてエクスポートします
export default {
  general: {
    // 共通文字列
    yes: `はい`,
    no: `いいえ`,
    confirm: `確認`,
    cancel: `キャンセル`,
    none: `なし`,
    unknown: `不明`,

    // デフォルト設定値
    defaults: {
      bot_name: `ともり`,
      base_trigger_words: ["トモリ", "ともり"],
    },

    // クールダウンメッセージ（スラッシュコマンド）
    cooldown_title: `⌛ お待ちください！`,
    cooldown: `再度 \`/{category}\` コマンドを使用するまで {seconds} 秒待つ必要があります。`,

    // メッセージトリガーのクールダウンメッセージ
    message_cooldown_title: `⌛ お待ちください！`,
    message_cooldown: `このサーバーの管理者がクールダウンを設定しています。**{botName}** に再度話しかけるには **{seconds}** 秒お待ちください。`,
    message_cooldown_footer_per_user: `サーバー設定: ユーザーごとのクールダウン`,
    message_cooldown_footer_per_channel: `サーバー設定: チャンネルごとのクールダウン`,
    message_cooldown_footer_server_wide: `サーバー設定: サーバー全体のクールダウン`,
    message_cooldown_footer_strict: `サーバー設定: 厳密サーバー全体のクールダウン`,

    // 標準的なインタラクションの応答（ボタン、セレクトメニュー）
    interaction: {
      cancel_title: `🔴 コマンドがキャンセルされました`,
      cancel_description: `コマンドはキャンセルされました。`,
      timeout_title: `⏰ コマンドがタイムアウトしました`,
      timeout_description: `時間内に応答しませんでした。もう一度お試しください。`,
    },

    // ページネーションコンポーネントのメッセージ
    pagination: {
      page_info: `ページ {current}/{total}`,
      previous: `前へ`,
      next: `次へ`,
      cancel: `キャンセル`,
      no_items: `表示する項目がありません。`,
      cancelled: `選択はキャンセルされました。`,
      timeout: `時間内に選択しませんでした。もう一度お試しください。`,
      item_selected: `選択済み: {item}`,
      select_page_title: `ページを選択`,
      select_page_description: `{totalItems}項目から{totalPages}ページ中の表示するページを選択してください：`,
      select_persona_title: `ペルソナを選択`,
      select_persona_description: `まず対象のペルソナを選択してください:\n\n{items}`,
      select_persona_description_v2: `まず対象のペルソナを選択してください。`,
      persona_main_badge: `メイン`,
      persona_alter_badge: `オルタ`,
      persona_no_attributes: `属性はまだ設定されていません。`,
      persona_select_button: `選択`,
    },

    // 一般的なエラーメッセージ
    errors: {
      guild_only_title: `サーバー専用コマンド`,
      guild_only_description: `このコマンドはサーバー内でのみ使用できます。`,
      guild_only_command_title: `サーバー専用コマンド`,
      guild_only_command_description: `このコマンドはサーバー内でのみ使用でき、ダイレクトメッセージでは使用できません。`,
      channel_only_title: `チャンネルが必要です`,
      channel_only_description: `このコマンドは正常に動作するためにチャンネルが必要です。`,
      channel_not_supported_title: `サポートされていないチャンネルタイプ`,
      channel_not_supported_description: `申し訳ありませんが、サーバーのテキストチャンネルまたはダイレクトメッセージでのみ動作します。グループDMやその他のチャンネルタイプはサポートされていません。`,
      tomori_not_setup_title: `初期設定が必要です`,
      tomori_not_setup_description: `このサーバーではまだ私の設定が行われていないようです。\`サーバー管理\`権限を持つメンバーが最初に\`/config setup\`を使用する必要があります。`,
      tomori_updating_title: `現在アップデート中...`,
      tomori_updating_description: `現在アップデート中のため、まもなく復旧します。しばらくしてからもう一度お試しください！`,
      tomori_not_setup_dm_footer: `DMは「ミニサーバー」として扱われ、私はあなたのメッセージに個人的に応答します。ほとんどのサーバー関連コマンドは意図通りに動作します。`,
      api_key_missing_title: `APIキーがありません`,
      api_key_missing_description: `機能するにはAPIキーが必要ですが、このサーバーには設定されていません。\`サーバー管理\`権限を持つメンバーが\`/config apikey set\`を使用して設定できます。`,
      api_key_error_title: `APIキーエラー`,
      api_key_error_description: `設定されたAPIキーへのアクセスまたは復号化で問題が発生しました。\`/config apikey set\`を使用して正しく設定されているか確認してください。`,
      context_error_title: `コンテキスト構築エラー`,
      context_error_description: `会話のコンテキストを理解しようとしているときにエラーが発生しました。`,
      critical_error_title: `重大なエラー`,
      critical_error_description: `予期しない重大なエラーが発生しました。`,
      update_failed_title: `更新に失敗しました`,
      update_failed_description: `データベースの設定の更新に失敗しました。もう一度お試しください。`,
      unknown_error_title: `不明なエラー`,
      unknown_error_description: `予期しないエラーが発生しました。問題が解決しない場合は、\`/support discord\`で報告してください。`,
      unexpected_title: `予期しないエラー`,
      unexpected_description: `予期しないエラーが発生しました：{error}`,
      invalid_option_title: `無効なオプション`,
      invalid_option_description: `選択されたオプションは無効です。有効なオプションを選択してください。`,
      permission_denied_title: `権限がありません`,
      permission_denied_description: `このコマンドを使用する権限がありません。\`サーバー管理\`権限を持つメンバーのみがこのコマンドを使用できます。`,
      server_not_found_title: `サーバーが見つかりません`,
      server_not_found_description: `データベースにサーバー情報が見つかりませんでした。もう一度お試しいただくか、問題が解決しない場合はサポートにお問い合わせください。`,
      generic_error_title: `エラー`,
      generic_error_description: `リクエストの処理中にエラーが発生しました。後でもう一度お試しください。`,
      brave_api: {
        missing_key: {
          title: `Brave APIキーがありません`,
          description: `検索を実行するにはBrave Search APIキーが必要ですが、このサーバーには設定されていません。\`サーバー管理\`権限を持つメンバーが\`/optionalkey brave set\`を使用して設定できます。`,
          footer: `/help apikeyで詳細を確認してください`,
        },
      },
      duckduckgo_rate_limit: {
        title: `DuckDuckGoがレート制限されています`,
        description: `DuckDuckGo検索は現在レート制限されています。より信頼性の高い検索のために、\`サーバー管理\`権限を持つメンバーが\`/optionalkey brave set\`を使用してBrave Searchを設定できます。`,
        footer: `/help apikeyで詳細を確認してください`,
      },
      operation_failed_title: `操作に失敗しました`,
      operation_failed_description: `要求された操作を完了できませんでした。もう一度お試しください。`,
      provider_not_supported_title: `サポートされていないプロバイダー`,
      provider_not_supported_description: `選択されたAIプロバイダーは現在サポートされていません。`,
      user_blacklisted_title: `ユーザーがブラックリスト登録済み`,
      user_blacklisted_description: `あなたは現在このサーバーのパーソナライズ機能のブラックリストに登録されており、この操作を実行できません。`,
      persona_response_failed_title: `ペルソナの応答に失敗しました`,
      persona_response_failed_description: `ペルソナ **{personaName}** からの応答の生成に失敗しました。もう一度お試しください。`,
      webhook_missing_permissions_title: `Webhook 権限がありません`,
      webhook_missing_permissions_description: `このチャンネルでWebhookを作成できないため、オルタペルソナは通常メッセージで返信します。**Webhookの管理**権限を付与すると、オルタのアバターを表示できます。`,
      webhook_limit_title: `Webhookの上限に達しました`,
      webhook_limit_description: `このチャンネルはDiscordのWebhook上限(10)に達しているため、オルタペルソナは通常メッセージで返信します。不要なWebhookを削除するか、オルタの数を減らしてください。`,
      webhook_unknown_error_title: `Webhook エラー`,
      webhook_unknown_error_description: `このチャンネルでWebhookを作成できなかったため、オルタペルソナは通常メッセージで返信します。権限を確認してもう一度お試しください。`,
      voice_transcription_unavailable_title: `音声文字起こしは利用できません`,
      voice_transcription_unavailable_description: `ここではまだ音声文字起こしを利用できません。\`/optionalkey elevenlabs set\` でElevenLabsキーを設定してから、もう一度お試しください。`,
      voice_transcription_failed_title: `音声文字起こしに失敗しました`,
      voice_transcription_failed_description: `その音声メッセージを文字起こしできませんでした。もう一度試すか、代わりにテキストで送信してください。`,
    },
    tomori_busy_title: "他の人に返信中です！",
    tomori_busy_replying:
      "現在このメッセージに返信中です: {message_link}。あなたのメッセージはキューに追加されました。",
  },

  rate_limit: {
    // ユーザーレベルのレート制限（DM通知）
    user_exceeded_title: `🟡️ レート制限に達しました`,
    user_exceeded_description: `現在、全サーバーで多数のアクティブなメッセージを処理中です。不正利用を防ぐため、最新のトリガー試行は破棄されました。メッセージの処理が完了するまでお待ちください。`,

    // サーバーレベルのレート制限（パブリックチャンネル通知）
    server_exceeded_title: `🟡️ サーバー過負荷`,
    server_exceeded_description: `このサーバーでは現在多数のアクティブなメッセージを処理中です。現在キャパシティに達しています！しばらく待ってから再度お試しいただくか、他のサーバーやダイレクトメッセージでご利用ください。`,

    error_memory_critical_title: `🔴 システム過負荷`,
    error_memory_critical_description: `現在メモリ使用率が高く、ファイルアップロードができません。しばらく後にお試しください。`,

    error_quota_exceeded_title: `🔴 1日の上限に達しました`,
    error_quota_exceeded_description: `このコマンドの1日の上限に達しました。クォータは**{reset_time}**にリセットされます。リセット時刻以降に再度お試しください。`,
  },

  genai: {
    // LLM API生成に関するエラー
    generic_error_title: `生成エラー`,
    generic_error_description: `申し訳ありません、応答を生成中にエラーが発生しました ({error_message})。`,
    generic_error_footer:
      "`/tool refresh`を実行してからもう一度お試しください。問題が解決しない場合は、`/support discord`で報告してください。",
    error_stream_timeout_title: "接続タイムアウト",

    // プロバイダーエラー形式テンプレート
    provider_error_format:
      "{providerName} エラーコード {errorCode}: {apiMessage}。{tip}",
    error_stream_timeout_description:
      "この問題が続く場合、選択したAIプロバイダーに一時的な問題がある可能性があります。後でもう一度お試しいただくか、`/tool refresh`を使用してコンテキスト履歴をリフレッシュしてください。",

    // APIからの空の応答
    empty_response_title: `空の応答`,
    empty_response_description: `AIから空の応答を受け取りました。この問題が解決しない場合は、\`/tool refresh\`を使用してください。`,
    // 新規: 関数呼び出しの最大反復回数
    max_iterations_title: "思考ループ",
    max_iterations_streaming_description:
      "思考ループに陥り、リクエストを完了できませんでした。この問題が解決しない場合は、`/tool refresh`を使用してください。",

    // NAIツールリトライ回数超過
    nai_tool_retry_exhausted_title: "ツールエラー",
    nai_tool_retry_exhausted_description:
      "ツールが複数回失敗し、リクエストを完了できませんでした。もう一度お試しいただくか、問題が解決しない場合は `/tool refresh` を使用してください。",

    // フォールバックモデル使用通知（プライマリが失敗したがフォールバックが成功した場合）
    fallback_used_title: `フォールバックモデルを使用しました`,
    fallback_used_description: `{chain} の代わりに \`{success_model}\` が使用されました`,

    // 一般的な応答なし警告（不明なステータスまたは未処理のケース用）
    no_response_title: `応答なし`,
    no_response_description: `応答がありませんでした - これはAIからの空の応答またはタイムアウトが原因である可能性があります。`,
    thought_log: {
      title: `思考ログ`,
      description: `元チャンネル: {source_line}`,
      summary_field: `思考サマリー`,
      raw_field: `生の思考`,
      footer: `プロバイダー: {provider} | モデル: {model}`,
    },

    // テキストクォータエラー
    text_quota_exceeded_title: `🔴 テキストクォータを超過しました`,
    text_quota_exceeded_description: `テキスト生成クォータに達しました。{reset_info}`,
    text_user_quota_exceeded_description: `日次テキスト生成クォータに達しました。{reset_info}`,
    text_serverwide_quota_exceeded_description: `このサーバーはこの期間のテキスト生成クォータに達しました。{reset_info}`,
    text_quota_resets_in_hours: `クォータは {hours} 時間後にリセットされます。`,
    text_quota_resets_in_days: `クォータは {days} 日後にリセットされます。`,
    text_quota_exceeded_footer: `このクォータは、このサーバーの管理者が \`/server quota\` で設定しています。`,

    // 検索関連メッセージ
    search: {
      web_search_title: `🔍 ウェブで \`{query}\` を検索中...`,
      image_search_title: `🔍 \`{query}\` の画像を検索中...`,
      video_search_title: `🔍 \`{query}\` の動画を検索中...`,
      news_search_title: `🔍 ニュースで \`{query}\` を検索中...`,
      disclaimer_description: `AIによる生成応答と検索結果は不正確または不完全な場合があります。**重要な情報は再確認してください**。`,
    },

    // カスタムMCPサーバーツール使用メッセージ
    mcp: {
      tool_invoke_title: `🔧 **{server}** の \`{function}\` を使用中...`,
      tool_invoke_description: `パラメーター:`,
      tool_invoke_no_params: `パラメーターなし。`,
    },

    // YouTube動画処理メッセージ
    video: {
      youtube_processing_title: "👁️ YouTube動画を視聴中...",
      youtube_processing_description:
        "現在、YouTube動画を視聴しています: {video_url}",
      youtube_processing_footer:
        "動画の長さに応じて、少し時間がかかる場合があります",
    },

    // インラインドキュメント読み取りメッセージ (read_document ツール)
    document: {
      reading_title: "📄 ドキュメントを読み取り中...",
      reading_description: "`{filename}` の内容を読み取っています",
    },

    image: {
      generating_title: "🖼️ 画像を生成中...",
      generating_description: "現在のプロンプトから画像を作成しています",
      generating_with_references_description:
        "現在のプロンプトと参照画像を使って画像を作成しています",
      editing_title: "🖌️ 画像を編集中...",
      editing_description:
        "参照画像の `{edit_target}` を対象に編集しています",
      generating_footer:
        "プロバイダーの混雑状況によって少し時間がかかる場合があります",
    },

    vision: {
      analyzing_title: "🖼️ 画像を解析中...",
      analyzing_description:
        "現在のモデルはビジョン非対応です。設定されたビジョンモデルを使用して画像を解析しています",
      analyzing_footer:
        "画像の数によって少し時間がかかる場合があります",
    },

    gif: {
      processing_title: "🎞️ GIFを処理中...",
      processing_description:
        "詳細に確認するため、指定されたGIFからキーフレームを抽出しています",
      processing_footer: "大きいGIFは少し時間がかかる場合があります",
    },

    fetch: {
      reading_title: "🌐 Webページを読み取り中...",
      reading_description: "{url} を取得して内容を読み取っています",
      reading_footer: "ページサイズによって少し時間がかかる場合があります",
    },

    // 新規: ストリーム固有のエラーメッセージ
    stream: {
      response_stopped_title: "応答が中断されました",
      response_stopped_description:
        "次の理由で応答が中断されました: {reason}。送信されたコンテンツがAIプロバイダーにとって大きすぎないか確認してください。`/tool refresh`で会話コンテンツをクリアしてください。",
      prohibited_content_title: "コンテンツポリシー違反",
      prohibited_content_description:
        "禁止コンテンツが検出されたため、応答はブロックされました。",
      prohibited_content_admin_notice_title: "管理者への通知",
      prohibited_content_admin_notice_description:
        "確認: メッセージ(`/tool refresh`)、性格/記憶(`/data export`)、問題のあるメンバーをブラックリスト(`/server blacklist`)、またはプロバイダを変更(`/config model`)",
      streaming_failed_description:
        "応答をストリーミング中に問題が発生しました。",

      // エラーインタラクションメッセージ
      provider_error_interaction:
        "ストリーム応答がブロック/停止されました。理由: {reason}。",
      retry_message: "これは一時的なエラーです。後でもう一度お試しください。",

      // 汎用プロバイダーエラータイトルとヒント（genai.googleから移動）
      api_error_title: "🔴 プロバイダーAPIエラー",
      api_error_tip:
        "APIキーを確認して再度お試しください。このエラーが解決しない場合は、`/support discord`で報告してください。",

      rate_limit_title: "🟡 プロバイダーレート制限を超過",
      rate_limit_title_all_rotation_keys:
        "🟡 全ローテーションキーがレート制限中",
      rate_limit_tip:
        "数分お待ちいただいてから再度お試しください。複数の個人キーをお持ちなら、`/config apikey rotation` の利用も検討してください。",
      model_fallback_hint:
        "耐障害性を高めるには、`/config model fallback` でモデルのフェイルオーバーを設定できます。",

      content_blocked_title: "🔴️ プロバイダーコンテンツフィルター",
      content_blocked_tip:
        "ヒント: `/config uncensors` でこのエラーの回避を試すか、メッセージ(`/tool refresh`)、性格/記憶(`/data export`)、問題のあるメンバーをブラックリスト(`/server blacklist`)、またはプロバイダを変更(`/config model`)を確認してください。",

      timeout_title: "🟡️ プロバイダーリクエストタイムアウト",
      timeout_tip: "メッセージを短くするか再度お試しください",

      provider_overloaded_title: "🔴 プロバイダーの過負荷",
      provider_overloaded_tip:
        "プロバイダーが現在過負荷状態です。しばらく後に再度お試しいただくか、別のプロバイダーに変更してください",

      unknown_title: "🔴 プロバイダーエラー",
      unknown_tip:
        "再度お試しいただくか、この問題が続く場合は `/support discord` をご利用ください",

      flush_limit_title: "🟡️ 応答の長さ制限に達しました",
      flush_limit_description:
        "この応答はメッセージの最大長制限に達したため停止されました。必要に応じて `/bot respond` を使用して手動で応答を続けることができます。",

      inactivity_timeout_title: "🟡️ 応答がタイムアウトしました",
      inactivity_timeout_description:
        "AIプロバイダーからの応答が停止し、接続がタイムアウトしました。プロバイダーが過負荷状態にあるか、問題が発生している可能性があります。もう一度お試しください。",
    },

    // Google固有のエラーメッセージ（プロバイダー固有のデフォルトメッセージのみ）
    google: {
      // 400 INVALID_ARGUMENT
      "400_default_message": "リクエスト形式にエラーがありました",

      // 400 FAILED_PRECONDITION (billing)
      "400_billing_default_message": "このサービスには課金が必要です",

      // 403 PERMISSION_DENIED
      "403_default_message":
        "APIキーに必要な権限がありません。Google AI Studioから合法的に取得した自分自身のAPIキーを使用していることを確認してください",

      // 404 NOT_FOUND
      "404_default_message": "参照されたリソースが見つかりませんでした",

      // 429 RESOURCE_EXHAUSTED
      "429_default_message": "短時間に多くのリクエストを送信しすぎました",

      // 500 INTERNAL
      "500_default_message": "Googleのサーバーで予期しないエラーが発生しました",

      // 503 UNAVAILABLE
      "503_default_message": "AIモデルが現在過負荷状態です",

      // 504 DEADLINE_EXCEEDED
      "504_default_message": "リクエストの処理時間が長すぎました",

      // Content blocked errors
      content_blocked_default_message:
        "あなたのコンテンツは安全フィルターによってブロックされました",

      // Generic fallback for unknown Google errors
      unknown_default_message: "予期しないエラーが発生しました",
    },

    // NovelAI固有のエラーメッセージ（プロバイダー固有のデフォルトメッセージのみ）
    novelai: {
      // 400 BAD_REQUEST
      "400_default_message": "無効なリクエスト形式またはパラメータ",

      // 400 BAD_REQUEST - Trial account recaptcha requirement
      "400_trial_message":
        "トライアルアカウントでは生成にrecaptcha認証が必要です。API経由のアクセスには有料のNovelAIサブスクリプションが必要です。https://novelai.net/ でアカウントをアップグレードしてください",

      // 401 UNAUTHORIZED
      "401_default_message": "NovelAIのAPIキーが無効または期限切れです",

      // 402 PAYMENT_REQUIRED
      "402_default_message": "Anlasクレジットが不足しています",

      // 429 TOO_MANY_REQUESTS
      "429_default_message":
        "リクエストを送信しすぎています。ペースを落としてください",

      // 503 SERVICE_UNAVAILABLE
      "503_default_message": "NovelAIサーバーが現在過負荷状態です",

      // 504 GATEWAY_TIMEOUT
      "504_default_message": "リクエストの処理時間が長すぎました",

      // Generic fallback for unknown NovelAI errors
      unknown_default_message: "予期しないエラーが発生しました",
    },

    // OpenRouter固有のエラーメッセージ（プロバイダー固有のデフォルトメッセージのみ）
    openrouter: {
      // 400 BAD_REQUEST
      "400_default_message":
        "不正なリクエスト：無効または欠落したパラメータ、またはCORSの問題",

      // 401 UNAUTHORIZED
      "401_default_message":
        "無効な認証情報：OAuthセッションの期限切れ、または無効/無効化されたAPIキー",

      // 402 PAYMENT_REQUIRED
      "402_default_message":
        "アカウントまたはAPIキーのクレジットが不足しています。クレジットを追加して再試行してください。",

      // 403 FORBIDDEN
      "403_default_message":
        "選択したモデルはモデレーションが必要で、入力がフラグされました",

      // 404 NOT_FOUND
      "404_default_message":
        "要求された機能（ツール/画像）をサポートするエンドポイントが見つかりません。`/config model text`コマンドを使用して別のモデルをお試しください。",

      // 404 Privacy Policy Error
      "404_privacy_policy_error":
        "**プライバシーポリシー制限**\n" +
        "選択したモデルは有料モデルトレーニングのためのデータ使用を許可する必要がありますが、OpenRouterアカウントのプライバシー設定で現在ブロックされています。\n\n" +
        "**修正方法：**\n" +
        "1. https://openrouter.ai/settings/privacy にアクセス\n" +
        "2. 「Data Policy」設定を調整してこのモデルを許可\n" +
        "3. またはプライバシー設定に一致する別のモデルを選択",

      // 408 REQUEST_TIMEOUT
      "408_default_message": "リクエストがタイムアウトしました",

      // 413 PAYLOAD_TOO_LARGE
      "413_default_message":
        "リクエストボディが大きすぎます（コンテキスト/メディアがプロバイダーの制限を超えています）。`/tool refresh`で会話履歴をクリアするか、コンテキスト内のメディア/記憶の量を減らしてください。",

      // 429 TOO_MANY_REQUESTS
      "429_default_message":
        "レート制限中です。しばらくしてから再試行するか、無料ではないモデルを使用してください。",

      // 502 BAD_GATEWAY
      "502_default_message":
        "選択したモデルがダウンしているか、無効な応答を受信しました",

      // 503 SERVICE_UNAVAILABLE
      "503_default_message":
        "ルーティング要件を満たす利用可能なモデルプロバイダーがありません",

      // invalid_type error (parameter type mismatch)
      invalid_type_default_message:
        "リクエストに無効な型のパラメータが含まれています。選択したモデルとの互換性の問題の可能性があります。`/tool refresh`でコンテキストをクリアするか、別のモデルをお試しください。",

      // Generic fallback for unknown OpenRouter errors
      unknown_default_message: "予期しないエラーが発生しました",
    },

    deepseek: {
      connection_refused:
        "DeepSeek APIエンドポイントに接続できませんでした。しばらくしてから再度お試しください。",

      "401_default_message":
        "DeepSeekのAPIキーが無効か、このモデルへのアクセス権がありません。",

      "402_default_message":
        "このリクエストを実行するためのDeepSeekクレジットが不足しています。",

      "403_default_message":
        "DeepSeekによってこのリクエストが拒否されました。アカウント状態とモデル権限を確認してください。",

      "404_default_message":
        "要求されたDeepSeekモデルまたはAPIルートが見つかりませんでした。",

      "408_default_message":
        "DeepSeekからの応答前にリクエストがタイムアウトしました。",

      "429_default_message":
        "DeepSeekでレート制限が発生しています。しばらくしてから再度お試しください。",

      "429_plan_access_default_message":
        "ご利用中のDeepSeekプランではこのモデルにアクセスできません。`/config model text` で別のモデルに切り替えてください。",

      "500_default_message": "DeepSeekで内部サーバーエラーが発生しました。",

      "503_default_message": "DeepSeekは現在利用できないか、過負荷状態です。",

      unknown_default_message:
        "DeepSeekとの通信中に予期しないエラーが発生しました。",
    },

    nvidia: {
      connection_refused:
        "NVIDIA APIエンドポイントに接続できませんでした。しばらくしてから再度お試しください。",

      "401_default_message":
        "NVIDIAのAPIキーが無効か、このモデルへのアクセス権がありません。",

      "402_default_message":
        "このリクエストを実行するためのNVIDIAクレジットが不足しています。",

      "403_default_message":
        "NVIDIAによってこのリクエストが拒否されました。アカウント状態とモデル権限を確認してください。",

      "404_default_message":
        "要求されたNVIDIAモデルまたはAPIルートが見つかりませんでした。",

      "408_default_message":
        "NVIDIAからの応答前にリクエストがタイムアウトしました。",

      "429_default_message":
        "NVIDIAでレート制限が発生しています。しばらくしてから再度お試しください。",

      "500_default_message": "NVIDIAで内部サーバーエラーが発生しました。",

      "503_default_message": "NVIDIAは現在利用できないか、過負荷状態です。",

      unknown_default_message:
        "NVIDIAとの通信中に予期しないエラーが発生しました。",
    },

    // Z.aiプロバイダー固有のエラーメッセージ
    zai: {
      connection_refused:
        "Z.ai APIエンドポイントに接続できませんでした。しばらくしてから再度お試しください。",

      "401_default_message":
        "Z.aiのAPIキーが無効か、このモデルへのアクセス権がありません。",

      "402_default_message":
        "このリクエストを実行するためのZ.aiクレジットが不足しています。",

      "403_default_message":
        "Z.aiによってこのリクエストが拒否されました。アカウント状態とモデル権限を確認してください。",

      "404_default_message":
        "要求されたZ.aiモデルまたはAPIルートが見つかりませんでした。",

      "429_default_message":
        "Z.aiでレート制限が発生しています。しばらくしてから再度お試しください。",

      "429_balance_default_message":
        "このリクエストを実行するためのZ.ai残高またはクレジットが不足しています。",

      "429_plan_access_default_message":
        "ご利用中のZ.aiプランではこのモデルにアクセスできません。`/config model text` で別のモデルに切り替えてください。",

      "500_default_message": "Z.aiで内部サーバーエラーが発生しました。",

      "503_default_message": "Z.aiは現在利用できないか、過負荷状態です。",

      unknown_default_message:
        "Z.aiとの通信中に予期しないエラーが発生しました。",
    },

    // カスタムプロバイダー固有のエラーメッセージ（セルフホスト型のOpenAI互換エンドポイント用）
    custom: {
      // 接続エラー
      connection_refused:
        "カスタムエンドポイントに接続できませんでした。ローカルLLMサーバーが起動しており、設定されたURLでアクセス可能であることを確認してください。",

      // HTTPステータスエラー
      "401_default_message":
        "認証に失敗しました。エンドポイントがAPIキーを必要とする場合は、正しく設定されているか確認してください。",

      "403_default_message":
        "カスタムエンドポイントによってアクセスが拒否されました。エンドポイントのアクセス制御を確認してください。",

      "404_default_message":
        "リソースが見つかりません。Ollamaユーザーの場合：モデル名が正しいか確認してください（`/config setup`で更新可能）。それ以外の場合は、エンドポイントURLに適切なパス（例：/v1/chat/completions）が含まれているか確認してください。",

      "408_default_message":
        "リクエストがタイムアウトしました。カスタムエンドポイントの応答に時間がかかりすぎました。",

      "429_default_message":
        "カスタムエンドポイントからレート制限を受けています。しばらくしてから再度お試しください。",

      "500_default_message":
        "カスタムエンドポイントで内部サーバーエラーが発生しました。LLMサーバーのログを確認してください。",

      "502_default_message":
        "バッドゲートウェイエラー。カスタムエンドポイントが無効な応答を返しました。",

      "503_default_message":
        "カスタムエンドポイントは現在利用できません。LLMサーバーが起動しているか確認してください。",

      // 汎用フォールバック
      unknown_default_message:
        "カスタムエンドポイントとの通信中に予期しないエラーが発生しました。",
    },

    self_teach: {
      server_memory_learned_title:
        "🧠 {persona_nickname}が新しいことを学びました！",
      server_memory_learned_description:
        "サーバー記憶を保存しました:\n`{memory_content}`",
      server_memory_updated_title:
        "📝 {persona_nickname}が記憶を更新しました！",
      server_memory_updated_description:
        "サーバー記憶を更新しました:\n`{memory_content}`",
      personal_memory_learned_title:
        "💡 {persona_nickname}が{user_nickname}さんについて新しいことを学びました！",
      personal_memory_learned_description:
        "{user_nickname}さんに関する個人的な記憶を保存しました:\n`{memory_content}`",
      personal_memory_updated_title:
        "📝 {persona_nickname}が{user_nickname}さんについての記憶を更新しました！",
      personal_memory_updated_description:
        "{user_nickname}さんに関する個人的な記憶を更新しました:\n`{memory_content}`",
      server_memory_footer:
        "サーバー管理者は`/teach`と`/forget`コマンドでこの記憶を管理できます。全文は`/data export`で確認できます。",
      personal_memory_footer_manage:
        "あなたの個人的な記憶は`/teach`と`/forget`コマンドで管理できます。全文は`/data export`で確認できます。個人記憶の保存は`/personal privacy`でオプトアウトできます。",
      personal_memory_footer_personalization_disabled:
        "この記憶は保存されましたが、現在このサーバーではパーソナライズ機能が無効になっているため、すぐには効果がありません。全文は`/data export`で確認できます。個人記憶の保存は`/personal privacy`でオプトアウトできます。",
      personal_memory_footer_user_blacklisted:
        "この記憶は保存されましたが、対象のユーザーは現在このサーバーのパーソナライズ機能のブラックリストに登録されているため、すぐには効果がありません。全文は`/data export`で確認できます。個人記憶の保存は`/personal privacy`でオプトアウトできます。",
    },
  },

  commands: {
    // 一般的なオプションに使用される再利用可能な選択肢のローカライゼーション
    choices: {
      add: "追加",
      remove: "削除",
      always: "常時",
      enable: "有効にする",
      disable: "無効にする",
      enabled: "有効",
      disabled: "無効",
      on: "オン",
      off: "オフ",
      yes: "はい",
      no: "いいえ",
      true: "真",
      false: "偽",
      opt_out: "記憶の保存をブロック",
      opt_in: "記憶の保存を許可",
      none: "なし",
      inherit_global: "グローバルクールダウンを継承",
    },

    // SillyTavernプリセット管理
    stpreset: {
      description: `SillyTavernプリセットを管理`,
      upload: {
        description: `SillyTavernプリセットJSONファイルをアップロード`,
        file_description: `アップロードするSillyTavernプリセットの.jsonファイル`,
        invalid_file_title: `無効なファイル`,
        invalid_format: `\`.json\`ファイルのみ対応しています。SillyTavernプリセットのJSONファイルをアップロードしてください。`,
        file_too_large_title: `ファイルが大きすぎます`,
        file_too_large_description: `プリセットファイルは{max_size} MB以下にしてください。`,
        download_failed: `添付ファイルのダウンロードに失敗しました。もう一度お試しください。`,
        invalid_json: `ファイルを有効なJSONとして解析できませんでした。`,
        not_a_preset: `これはSillyTavernプリセットではないようです — \`prompts\`配列が見つかりません。`,
        no_nodes: `このプリセットに使用可能なプロンプトノードが見つかりませんでした。`,
        duplicate_name: `"{name}"という名前のプリセットはこのサーバーに既に存在します。先に削除するか、ファイル名を変更してください。`,
        success_title: `プリセットをアップロードしました`,
        success_description: `**{name}**をインポートしました。\n\n• **{total}** 合計ノード\n• **{markers}** 構造マーカー\n• **{toggleable}** 切り替え可能ノード（**{enabled}** 有効）\n{notes}\n\`/stpreset node toggle\`でアクティブなノードを調整できます。\n\`/stpreset remove\`でデフォルトの動作に戻せます。`,
        note_comment_only: `\n> **{count}** 個のコメントのみのノードが���キップされました（\`{{// コメント}}\`のみで出力がないため）。`,
        note_disabled_by_preset: `\n> **{count}** 個のノードがこのプリセットでデフォルトで無効になっています。\`/stpreset node toggle\`で有効にできます。`,
      },
      remove: {
        description: `アクティブなSillyTavernプリセットを削除`,
        no_preset_title: `アクティブなプリセットがありません`,
        no_preset_description: `このサーバーにアクティブなSillyTavernプリセットがありません。削除するものがありません。`,
        failed_title: `削除に失敗しました`,
        failed_description: `プリセットの削除に失敗しました。もう一度お試しください。`,
        success_title: `プリセットを削除しました`,
        success_description: `**{name}**を削除しました。コンテキスト組み立てがデフォルトの動作に戻りました。`,
      },
      node: {
        description: `プリセットのプロンプトノードを管理`,
        toggle: {
          description: `プリセットのプロンプトノードのオン・オフを切り替え`,
          no_preset_title: `プリセットが見つかりません`,
          no_preset_description: `このサーバーにアクティブなSillyTavernプリセットがありません。まず\`/stpreset upload\`でアップロードしてください。`,
          no_nodes_title: `切り替え可能なノードがありません`,
          no_nodes_description: `このプリセットには切り替え可能なプロンプトノードがありません。`,
          select_page_title: `ページを選択`,
          select_page_description: `**{preset_name}**には**{total_nodes}**個の切り替え可能なノードが**{total_pages}**ページにわたってあります。\nページを選択してノードを表示・切り替え:`,
          group_description: `チェックで有効、チェック解除で無効`,
          done_button: `完了`,
          no_changes: `変更なし`,
          result_title: `ノード切り替え結果`,
          result_description: `**{enabled}** / **{total}** ノードが有効。\n\n{changes}`,
        },
      },
    },

    // 一般的なユーティリティコマンド
    tool: {
      ping: {
        description: `ボットの遅延を確認します`,
        title: `Pong! 🏓`,
        response_fast: `応答時間: \`{response_time}ms\``,
        response_slow: `応答時間: \`{response_time}ms\``,
      },
      estimate: {
        description: `利用量と費用の見積もり`,
        cost: {
          description: `有料AIプロバイダーのAPI費用を見積もる`,
          title: `推定API費用`,
          embed_description: `Discordチャンネルでのトリガーあたりの**非常におおまかな**推定費用です。費用は**{provider}**の例を使用して推定されています（入力：{inputPrice}/百万トークン、出力：{outputPrice}/百万トークン）`,
          current_context_description: `あなたの**現在のコンテキストのみ**を対象にした推定費用です。入力トークンは、現在の設定と直近のチャンネル履歴を使って、**{provider}** のモデル **{model}** でプロバイダーAPI計測を行います。出力トークンは推定値です。使用価格: 入力 {inputPrice}/百万、出力 {outputPrice}/百万。`,
          current_input_title: `計測済み入力トークン（現在のコンテキスト）`,
          current_input_value: `**入力:** {inputTokens} トークン\n**入力コストのみ:** 1トリガーあたり約 {inputCost}`,
          current_output_short_title: `推定出力: 短め`,
          current_output_typical_title: `推定出力: 標準`,
          current_output_long_title: `推定出力: 長め`,
          current_output_band_value: `**出力推定:** {outputTokens} トークン\n**合計推定:** {totalTokens} トークン\n**費用:** 1トリガーあたり約 {costPerMessage}（100トリガーあたり約 {costPer100}）`,
          current_footer: `入力トークンは、ライブ計測に対応したプロバイダーでのみプロバイダー計測値になります。出力トークンは推定値です。`,
          no_cost_provider_description: `現在のプロバイダーには費用がありません`,
          unavailable_description: `現在のプロバイダー（**{provider}**）ではライブ費用見積もりを利用できません。`,
          fallback_notice_title: `ライブ計測を利用できません`,
          fallback_notice_value: `現在の設定ではライブのプロバイダートークン計測を利用できなかったため、この表示はおおまかな代替推定です。`,
          minimum_scenario_title: `最小シナリオ（軽量使用）`,
          minimum_scenario_value: `**コンテキスト：** 1ユーザー、メモリなし、1段落のペルソナ、会話は1メッセージあたり1文未満
**トークン数：** {inputTokens} 入力 + {outputTokens} 出力 = {totalTokens} 合計
**費用：** ~{costPerMessage} /トリガー（~{costPer100} /100トリガー）`,
          average_scenario_title: `平均シナリオ（中程度使用）`,
          average_scenario_value: `**コンテキスト：** 3ユーザー（各10メモリ）、~16段落のペルソナ（属性と対話を含む）、会話は1メッセージあたり1〜2文
**トークン数：** {inputTokens} 入力 + {outputTokens} 出力 = {totalTokens} 合計
**費用：** ~{costPerMessage} /トリガー（~{costPer100} /100トリガー）`,
          maximum_scenario_title: `最大シナリオ（重量使用）`,
          maximum_scenario_value: `**コンテキスト：** 5ユーザー（各25メモリ）、~31段落のペルソナ（属性と対話を含む）、会話は1メッセージあたり2段落
**トークン数：** {inputTokens} 入力 + {outputTokens} 出力 = {totalTokens} 合計
**費用：** ~{costPerMessage} /トリガー（~{costPer100} /100トリガー）`,
          breakdown_title: `費用に影響する要因`,
          breakdown_value: `**入力トークン（AIに送信されるコンテキスト）：**
- ペルソナの段落数（属性とサンプル対話を含む）
- サーバー＆個人メモリ
- 有効化されたツール（ある場合）
- ユーザーステータス＆リマインダー
- 最近の会話履歴（プロバイダーがサポートしている場合、画像、動画、スタンプ、絵文字、埋め込みを含む）
- サーバー絵文字（常に10個）

**出力トークン（AI応答）：**
- 応答の長さはクエリの複雑さによって異なります
- より詳細な質問 = より長い応答 = より高い費用

**費用を削減するヒント：**
サーバー内の悪用者やスパマーによる費用を削減するための組み込み機能がありますが、以下の追加のヒントもあります：
- ペルソナの段落数を少なくする（属性と対話）
- メモリを簡潔に保つ
- 無料のAIプロバイダーを使用する（Google Gemini無料プラン）
- 自動トリガーチャンネルを制限する`,
          footer: `Google Gemini（無料プラン）や一部のOpenRouterモデルなどの無料プロバイダーは費用がかかりません！NovelAIはサブスクリプション制で無制限に使用できます。プロバイダーの詳細は\`/help apikey\`をご覧ください。`,
        },
      },
      compact: {
        description: `最近の会話をコンパクトなシステム要約にまとめます。`,
        channel_description: `要約を投稿するチャンネル（省略時はこのチャンネルに投稿）。`,
        modal: {
          title: `コンパクト要約`,
          type_label: `要約タイプ`,
          type_description: `生成する要約形式を選択してください。`,
          type_choice_conversation: `会話`,
          type_choice_roleplay: `ロールプレイ`,
          refresh_label: `コンテキストをリフレッシュ?`,
          refresh_description: `はいの場合、この要約より上のメッセージは無視されます。`,
          analyze_images_label: `画像を解析?`,
          analyze_images_description: `添付・絵文字・スタンプの画像解析を含めます。`,
          additional_instructions_label: `追加指示`,
          additional_instructions_placeholder: `任意: 要約への追加の指示を入力してください。`,
        },
        processing_title: `⏳ 要約中`,
        processing_description: `最近の会話を要約しています...`,
        success_title: `✅ 要約を投稿しました`,
        success_description: `コンパクト要約をこのチャンネルに投稿しました。`,
        success_description_redirect: `コンパクト要約を {channel} に投稿しました。`,
        failed_title: `要約に失敗しました`,
        failed_description: `要約の生成に失敗しました: {error}`,
        provider_unsupported_title: `未対応のプロバイダー`,
        provider_unsupported_description: `現在のプロバイダー ({provider}) はコンパクト要約に未対応です。対応プロバイダーに切り替えてください。`,
        model_incompatible_title: `モデル非対応`,
        model_incompatible_description: `現在のモデル ({model_name}) はロールプレイ要約に必要な構造化出力 (STRUCT) に対応していません。`,
        image_vision_required_title: `画像認識が必要`,
        image_vision_required_description: `現在のモデル ({model_name}) は画像解析に対応していません。画像解析をオフにするか、対応モデルを選択してください。`,
        summary_title: `🧠 コンパクト要約`,
        summary_title_refreshed: `🧹 コンパクト要約 (リフレッシュ)`,
        roleplay_scene_title: `🎭 ロールプレイのシーン要約`,
        roleplay_scene_title_refreshed: `🧹 ロールプレイのシーン要約 (リフレッシュ)`,
        roleplay_scene_synopsis_header: `現在のストーリーのあらすじ:`,
        roleplay_character_title_prefix: `🎭 キャラクター要約:`,
        roleplay_labels: {
          character: `キャラクター要約`,
          current_goals: `直近の目標`,
          emotional_status: `現在の感情状態`,
          physical_status: `現在の身体の状態`,
          appearance_clothing: `外見・服装`,
          inventory: `所持品`,
        },
        refresh_footer: `この埋め込みからコンテキストがリフレッシュされました。`,
      },
      refresh: {
        description: `最近の会話履歴をクリアします。`,
        title: `🧹 会話履歴がクリアされました`,
        response: `コンテキストがリフレッシュされました。これより上のすべてのメッセージは無視されます。`,
      },
      status: {
        description: `現在の個人、サーバー、またはペルソナのステータスを表示します。`,
        scope_description: `どのスコープのステータスを表示しますか？`,
        scope_choice_personal: `個人`,
        scope_choice_server: `サーバー`,
        scope_choice_persona: `ペルソナ`,
        // 個人スコープ（1ページ）
        personal_title: `個人ステータス`,
        personal_description: `あなたの個人設定とグローバル個人メモリ`,
        // サーバースコープ（5ページ）
        server_title: `サーバーステータス`,
        server_description: `サーバー設定とモデレーション設定`,
        server_page1_title: `サーバーステータス: モデルとサンプリング`,
        server_page1_description: `言語モデルとサンプラー設定`,
        server_page2_title: `サーバーステータス: 動作設定`,
        server_page2_description: `タイミング、上限、クールダウン設定`,
        server_page3_title: `サーバーステータス: チャンネルと自動化`,
        server_page3_description: `自動チャット、RPチャンネル、ホワイトリスト、ランダムトリガー`,
        server_page4_title: `サーバーステータス: 機能とモデレーション`,
        server_page4_description: `機能トグルとモデレーション設定`,
        server_page5_title: `サーバーステータス: システムプロンプト`,
        server_page5_description: `現在のサーバーシステムプロンプトのプレビュー`,
        server_page6_title: `サーバーステータス: モデル上書き`,
        server_page6_description: `チャンネルとペルソナのモデル上書き`,
        server_page7_title: `サーバーステータス: クォータ`,
        server_page7_description: `画像・テキストのクォータ設定を完全表示`,
        // ペルソナスコープ（ペルソナ選択＋5ページ）
        persona_page1_title: `{persona_name}: アイデンティティ`,
        persona_page1_description: `ペルソナのアイデンティティとトリガーワード`,
        persona_page2_title: `{persona_name}: 属性`,
        persona_page2_description: `ペルソナ属性の省略表示`,
        persona_page3_title: `{persona_name}: サンプル対話`,
        persona_page3_description: `ペルソナのサンプル対話ペアの省略表示`,
        persona_page4_title: `{persona_name}: 記憶`,
        persona_page4_description: `あなた向けのペルソナ個人メモリとサーバーメモリ`,
        persona_page5_title: `{persona_name}: プロンプトとタグ`,
        persona_page5_description: `ペルソナプロンプトと生成タグ`,
        // 共通フィールド
        field_model: `AIモデル`,
        field_temperature: `Temperature`,
        field_top_p: `Top-P`,
        field_top_k: `Top-K`,
        field_min_p: `Min-P`,
        field_frequency_penalty: `Frequency Penalty`,
        field_presence_penalty: `Presence Penalty`,
        field_humanizer: `ヒューマナイザーレベル`,
        field_timezone: `サーバータイムゾーン`,
        field_message_fetch_limit: `メッセージ取得上限`,
        field_autoch_threshold: `自動チャットモード`,
        field_autoch_channels: `自動チャットチャンネル`,
        field_rp_channels: `RPチャンネル`,
        field_thought_logs_channel: `思考ログチャンネル`,
        field_welcome_channel: `ウェルカムチャンネル`,
        field_welcome_persona: `ウェルカムペルソナ`,
        field_trigger_words: `トリガーワード`,
        field_whitelist_channels: `チャネルホワイトリスト`,
        field_whitelist_roles: `ロールホワイトリスト`,
        whitelist_all_allowed: `なし（全チャンネル許可）`,
        whitelist_roles_all_allowed: `なし（全ロール許可）`,
        field_random_triggers: `ランダムトリガー`,
        field_channel_llm_overrides: `チャンネルモデル上書き`,
        field_persona_llm_overrides: `ペルソナモデル上書き`,
        random_trigger_persona_random: `ランダム`,
        field_cooldown_type: `クールダウンタイプ`,
        field_cooldown_length: `クールダウン時間`,
        field_cooldown_length_value: `{seconds}秒`,
        field_self_reply_limit: `自己返信上限`,
        field_send_message_limit: `送信上限`,
        field_always_reply: `常時応答`,
        field_triggered_persona_limit: `トリガーペルソナ上限`,
        field_personalization: `個人の記憶`,
        field_self_teach: `自己学習`,
        field_pin_message: `メッセージピンツール`,
        field_hide_respond_embed: `応答埋め込みを非表示`,
        field_self_debug: `セルフデバッグエラー埋め込み`,
        field_blacklisted_members: `ブラックリスト登録済みメンバー`,
        field_api_key_set: `APIキー設定済み`,
        field_brave_api_key_set: `Brave APIキー設定済み`,
        field_emoji_usage: `絵文字使用`,
        field_sticker_usage: `スタンプ使用`,
        field_web_search: `ウェブ検索`,
        field_image_generation: `画像生成`,
        field_videogen: `動画生成`,
        field_server_memteaching: `サーバー記憶の学習`,
        field_attribute_memteaching: `属性の学習`,
        field_sampledialogue_memteaching: `サンプル対話の学習`,
        field_hide_impersonation: `なりすまし埋め込みを非表示`,
        field_uncensor_injection: `インジェクション対策プロンプト`,
        field_uncensor_unicode: `Unicode空白置換`,
        field_uncensor_sanitize: `ワードサニタイズ`,
        field_image_quota_enabled: `画像クォータ有効`,
        field_image_quota_daily_user: `画像 1日あたりユーザークォータ`,
        field_image_quota_serverwide: `画像 サーバー全体クォータ`,
        field_image_quota_reset_days: `画像クォータ リセット周期`,
        field_text_quota_enabled: `テキストクォータ有効`,
        field_text_quota_daily_user: `テキスト 1日あたりユーザークォータ`,
        field_text_quota_serverwide: `テキスト サーバー全体クォータ`,
        field_text_quota_reset_days: `テキストクォータ リセット周期`,
        field_quota_reset_days_value: `{days}日`,
        field_quota_unlimited: `無制限`,
        field_nickname: `ニックネーム`,
        field_dialogue_count: `サンプル対話`,
        field_attributes: `属性`,
        field_is_alter: `オルターペルソナ`,
        field_alter_triggers: `オルタートリガー`,
        field_persona_triggers: `ペルソナトリガー`,
        field_persona_model: `ペルソナモデル上書き`,
        persona_model_server_default: `サーバーデフォルト`,
        field_system_prompt: `システムプロンプト`,
        field_persona_prompt: `ペルソナプロンプト`,
        field_persona_prompt_not_set: `*(未設定)*`,
        field_nai_tags: `NAI画像タグ`,
        field_nai_attg: `NAI ATTGメタデータ`,
        nai_attg_not_set: `*(未設定)*`,
        field_user_nickname: `ユーザーニックネーム`,
        field_language_pref: `言語設定`,
        field_privacy: `プライバシーモード`,
        field_impersonation_prompt: `なりすましプロンプト`,
        field_impersonation_prompt_not_set: `*(未設定)*`,
        field_reminders_count: `アクティブなリマインダー`,
        field_personal_memories: `個人の記憶`,
        field_server_memories: `サーバーの記憶`,
        item_count: `{count} 件`,
        none: `なし`,
        disabled: `無効`,
        unknown_channel: `不明なチャンネルID:`,
        not_available: `N/A`,
        see_all_memories_prompt: `すべての記憶を表示するには \`/data export\` コマンドを使用してください`,
        memories_omitted: `...他 {count} 件の記憶が省略されました`,
        export_footer: `完全な記憶を表示するには \`/data export\` コマンドを使用してください`,
        export_footer_full: `すべての詳細を表示するには \`/data export\` コマンドを使用してください`,
        export_footer_global_personal_memories: `完全な値を表示するには \`/data export type:global_personal_memories\` を使用してください`,
        export_footer_persona_memories: `完全な値を表示するには \`/data export type:persona_personal_memories\` と \`/data export type:persona_server_memories\` を使用してください`,
        export_footer_persona_attributes_and_dialogues: `完全な属性とサンプル対話を表示するには \`/persona export\` を使用してください`,
        export_footer_server_config: `完全な値を表示するには \`/data export type:server_config\` を使用してください`,
        field_personal_memories_with_count: `個人の記憶 ({current}/{max} 枠使用中)`,
        field_global_personal_memories_with_count: `グローバル個人メモリ ({current}/{max} 枠使用中)`,
        field_trigger_words_with_count: `トリガーワード ({current}/{max} 枠使用中)`,
        field_attributes_with_count: `属性 ({current}/{max} 枠使用中)`,
        field_sample_dialogues_with_count: `サンプル対話 ({current}/{max} 枠使用中)`,
        field_persona_personal_memories_with_count: `ペルソナ個人メモリ ({current}/{max} 枠使用中)`,
        field_persona_server_memories_with_count: `ペルソナサーバーメモリ ({current}/{max} 枠使用中)`,
        field_slot_usage: `{current}/{max} 枠使用中`,
        field_server_memories_with_count: `サーバーの記憶 ({current}/{max} 枠使用中)`,
        field_dialogue_count_with_count: `{current}/{max} 枠使用中`,
        field_blacklisted_members_with_count: `{current} 人`,
      },
      comment: {
        description: `チャットに表示されるが、コンテキストには表示されないコメントを送信します。`,
        modal_title: `コメントを作成`,
        content_label: `コメント内容`,
        content_placeholder: `ここにコメントを入力してください...`,
        invalid_channel_title: `無効なチャンネル`,
        invalid_channel_description: `このコマンドはテキストチャンネルでのみ使用できます。`,
        footer: `{user}によるコメント、コンテキストには非表示`,
        success_title: `コメント投稿済み`,
        success_description: `コメントがこのチャンネルに投稿されました。`,
      },
      delete: {
        description: `ターンやチャンネルのコンテンツを削除します。`,
        turn: {
          description: `チャンネルから最後のペルソナのターンを削除します。`,
          regenerate_description: `trueの場合、削除後にペルソナを再トリガーします。`,
          select_persona_description: `trueの場合、削除するペルソナのターンを選択できます。`,
          no_permission_title: `権限が不足しています`,
          no_permission_description: `このコマンドにはサーバー管理権限が必要か、指定されたRPチャンネルで使用する必要があります。`,
          already_running_title: `削除中です`,
          already_running_description: `このチャンネルではすでに削除処理が進行中です。しばらくお待ちください。`,
          no_persona_found_title: `ペルソナのターンが見つかりません`,
          no_persona_found_description: `最近の履歴にペルソナの連続したメッセージブロックが見つかりませんでした。`,
          deleting_title: `⏳ ターンを削除中`,
          deleting_description: `**{persona_name}** の {count} 件のメッセージを削除中...`,
          success_title: `✅ ターンが削除されました`,
          success_description: `**{persona_name}** の {count} 件のメッセージを削除しました。`,
          success_regenerate_description: `**{persona_name}** の {count} 件のメッセージを削除しました。再トリガー中...`,
          partial_title: `⚠️ 一部削除されました`,
          partial_description: `**{persona_name}** の {deleted_count}/{total_count} 件のメッセージを削除しました。一部のメッセージは削除できませんでした。`,
        },
      },
    },

    // データ管理コマンド
    data: {
      description: `データのエクスポートとインポートを管理する`,
      export: {
        description: `特定のデータをJSONバックアップとしてエクスポートする`,
        type_description: `何をエクスポートしますか？`,
        scope_description: `選択したデータタイプのスコープを選択してください`,
        type_choice_personal: `個人データ`,
        type_choice_server: `サーバーデータ`,
        type_choice_personality: `性格情報`,
        type_choice_persona_personal_memories: `ペルソナの個人メモリ`,
        type_choice_persona_server_memories: `ペルソナのサーバーメモリ`,
        type_choice_personal_settings: `個人設定`,
        type_choice_server_config: `サーバー設定`,
        type_choice_global_personal_memories: `グローバル個人メモリ`,
        scope_choice_persona: `ペルソナ`,
        scope_choice_global: `グローバル`,
        scope_choice_serverwide: `サーバー全体`,
        persona_modal_title: `ペルソナを選択`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `記憶データをエクスポートする対象ペルソナを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        success_title: `🟢 エクスポート成功`,
        success_description: `{type}データがDMに送信されました！`,
        success_description_personality: `私の性格がエクスポートされ、DMに送信されました！\n\n**注意:** このエクスポートは情報提供のみを目的としています。性格をインポートするには、代わりに\`/persona\`コマンドを使用してください。`,
        failed_title: `🔴 エクスポート失敗`,
        failed_description: `データのエクスポートに失敗しました。後でもう一度お試しください。`,
        dm_title: `データエクスポート`,
        dm_description: `リクエストされた{type}データをお送りします！`,
        dm_description_server: `リクエストされたサーバーデータをお送りします！\n\n**注意:** セキュリティのため、トリガーワードとAPIキーは除外されています。インポート後に手動で再設定する必要があります。`,
        dm_description_personality: `リクエストされた性格情報をお送りします！\n\n**注意:** このテキストファイルは情報提供のみを目的としています。サーバーに性格をインポートするには、代わりに\`/persona\`コマンドを使用してください。`,
        dm_failed_title: `🔴 DMを送信できませんでした`,
        dm_failed_description: `DMを送信できませんでした。サーバーメンバーからのDMを有効にしてから、もう一度お試しください。`,
        no_permission_title: `🔴 権限がありません`,
        no_permission_description: `サーバーデータをエクスポートするには**サーバー管理**権限が必要です。`,
        invalid_scope_title: `🔴 無効なスコープ`,
        invalid_scope_personal_description: `個人データのエクスポートでは \`serverwide\` スコープは使用できません。`,
        invalid_scope_server_description: `サーバーデータのエクスポートでは \`global\` スコープは使用できません。`,
        invalid_scope_personality_description: `性格情報のエクスポートで有効なのは \`persona\` スコープのみです。`,
        // dataExportユーティリティからのエラーメッセージ
        error_no_user_data: `ユーザーデータが見つかりません。まずボットとやり取りする必要があるかもしれません。`,
        error_no_server_data: `サーバーがデータベースに見つかりません。まず /config setup を実行してください。`,
        error_no_server_config: `サーバー設定が見つかりません。まず /config setup を実行してください。`,
        error_no_personality_data: `このサーバーの性格データが見つかりません。まず /config setup を実行してください。`,
        error_validation_failed: `エクスポートデータ構造の検証に失敗しました`,
        error_export_failed: `データのエクスポートに失敗しました`,
      },
      import: {
        description: `エクスポート済みJSONファイルからデータをインポートする（自動判別）`,
        file_description: `データをインポートするJSONファイル`,
        confirmation_description: `警告：ファイルの種類に応じて既存データが置き換えられる場合があります。続行しますか？`,
        confirmation_description_server: `警告：サーバー設定と記憶が置き換えられます。復元されないもの：トリガーワード、APIキー、性格、アバター。`,
        scope_description: `インポートデータを適用するスコープを選択してください`,
        confirmation_choice_yes: `はい、理解した上で続行します`,
        confirmation_choice_no: `いいえ、インポートをキャンセルします`,
        scope_choice_persona: `ペルソナ`,
        scope_choice_global: `グローバル`,
        scope_choice_serverwide: `サーバー全体`,
        persona_modal_title: `ペルソナを選択`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `このインポートを適用するペルソナを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        global_option_label: `グローバル`,
        global_option_description: `グローバルはペルソナに紐づかない共有メモリスコープを意味します。`,
        legacy_personal_label: `旧形式の個人バックアップ`,
        legacy_server_label: `旧形式のサーバーバックアップ`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        success_title: `🟢 インポート成功`,
        success_description: `{type}データを正常にインポートしました！\nインポートされたメモリ: {memories_count}\n 更新された設定フィールド: {config_count}`,
        success_description_server: `サーバーデータを正常にインポートしました！\n記憶: {memories_count}\n 設定: {config_count}\n\n**注意:** トリガーワードとAPIキーはインポートされませんでした。必要に応じて別途設定してください。`,
        success_description_server_persona_scope: `選択したペルソナスコープでサーバーデータを正常にインポートしました！\n記憶: {memories_count}\n 設定: {config_count}\n\n**注意:** サーバー設定はサーバー全体に適用されます。トリガーワードとAPIキーはインポートされません。`,
        failed_title: `🔴 インポート失敗`,
        failed_description: `データのインポートに失敗しました。ファイルを確認してもう一度お試しください。`,
        cancelled_title: `🔴 インポートがキャンセルされました`,
        cancelled_description: `インポートがキャンセルされました。データは変更されていません。`,
        invalid_file_type_title: `🔴 無効なファイルタイプ`,
        invalid_file_type_description: `有効な.jsonファイルをアップロードしてください。`,
        file_too_large_title: `🔴 ファイルが大きすぎます`,
        file_too_large_description: `ファイルが大きすぎます。最大ファイルサイズは1MBです。`,
        parse_failed_title: `🔴 無効なJSON`,
        parse_failed_description: `ファイルが有効なJSONファイルではありません。ファイル形式を確認してください。`,
        invalid_file_title: `🔴 無効なインポートファイル`,
        invalid_file_description: `インポートファイルの形式が無効または互換性がありません。`,
        no_permission_title: `🔴 権限がありません`,
        no_permission_description: `サーバーデータをインポートするには**サーバー管理**権限が必要です。`,
        invalid_scope_title: `🔴 無効なスコープ`,
        invalid_scope_personal_description: `個人データのインポートでは \`serverwide\` スコープは使用できません。`,
        invalid_scope_server_description: `サーバーデータのインポートでは \`global\` スコープは使用できません。`,
        error_download_timeout: `ファイルのダウンロードがタイムアウトしました。もう一度お試しください。`,
        error_download_failed: `インポートファイルのダウンロードに失敗しました。`,
        // dataImportユーティリティからのエラーメッセージ
        error_invalid_memory: `無効なメモリコンテンツ: {details}`,
        error_update_failed: `データベースのユーザーデータの更新に失敗しました`,
        error_import_failed: `データのインポートに失敗しました`,
        error_no_server_data: `サーバーがデータベースに見つかりません。まず /config setup を実行してください。`,
        error_invalid_server_memory: `無効なサーバーメモリコンテンツ: {details}`,
        error_invalid_config: `インポートデータに無効な設定フィールドがあります`,
        error_no_users: `データベースにユーザーが見つかりません。サーバーメモリを帰属できません。`,
        error_not_json: `インポートファイルは有効なJSONオブジェクトである必要があります`,
        error_incompatible_version: `互換性のないインポートバージョン。期待値: {expected}、実際値: {actual}`,
        error_invalid_personal_format: `無効な個人インポートファイル形式`,
        error_invalid_server_format: `無効なサーバーインポートファイル形式`,
        error_invalid_personal_memories_format: `無効な個人メモリインポートファイル形式`,
        error_invalid_server_memories_format: `無効なサーバーメモリインポートファイル形式`,
        error_invalid_personal_settings_format: `無効な個人設定インポートファイル形式`,
        error_invalid_server_config_format: `無効なサーバー設定インポートファイル形式`,
        error_unknown_type: `不明なインポートタイプ: {type}`,
      },
      delete: {
        description: `選択したデータスコープを完全に削除する`,
        type_description: `何を削除しますか？`,
        scope_description: `任意のスコープ（空欄なら従来どおりの全削除）`,
        type_choice_personal: `個人データ`,
        type_choice_server: `サーバーデータ`,
        type_choice_persona_personal_memories: `ペルソナの個人メモリ`,
        type_choice_persona_server_memories: `ペルソナのサーバーメモリ`,
        type_choice_personal_settings: `個人設定`,
        type_choice_server_config: `サーバー設定`,
        type_choice_global_personal_memories: `グローバル個人メモリ`,
        scope_choice_persona: `ペルソナ`,
        scope_choice_global: `グローバル`,
        scope_choice_serverwide: `サーバー全体`,
        confirmation_description: `完全削除を確認（これは元に戻せません！）`,
        confirmation_yes: `はい、完全に削除します - 元に戻せないことを理解しています`,
        confirmation_no: `いいえ、削除をキャンセルします`,
        persona_modal_title: `ペルソナを選択`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `削除するペルソナスコープを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        confirmation_required_title: `確認が必要です`,
        confirmation_required_description: `削除を確認するには確認オプションを選択する必要があります。`,
        invalid_scope_title: `🔴 無効なスコープ`,
        invalid_scope_personal_description: `個人データの削除では \`serverwide\` スコープは使用できません。`,
        invalid_scope_server_description: `サーバーデータの削除では \`global\` スコープは使用できません。`,
        success_memory_scope_title: `🟢 スコープ付きメモリ削除が完了しました`,
        success_persona_memories_description: `ペルソナ「{persona_name}」の個人メモリを {memory_count} 件削除しました。`,
        success_global_memories_description: `グローバル個人メモリを {memory_count} 件削除しました。`,
        success_persona_server_memories_description: `ペルソナ「{persona_name}」のサーバーメモリを {memory_count} 件削除しました。`,
        success_personal_title: `🟢 個人データが削除されました`,
        success_personal_description: `すべての個人データが完全に削除されました。再び私とやり取りすると、デフォルト設定で新規開始します。`,
        success_server_title: `🟢 サーバーデータが削除されました`,
        success_server_description: `すべてのサーバーデータが完全に削除されました。再び私を使用するには \`/config setup\` を実行する必要があります。`,
        success_personal_settings_title: `🟢 個人設定をリセットしました`,
        success_personal_settings_description: `個人設定をデフォルトに戻しました。`,
        success_server_config_title: `🟢 サーバー設定をリセットしました`,
        success_server_config_description: `サーバー設定をデフォルトに戻しました。`,
        no_data_title: `🟡️ データが見つかりません`,
        no_data_description: `データベースに個人データが保存されていません。`,
        no_persona_memories_description: `ペルソナ「{persona_name}」に個人メモリはありません。`,
        no_global_memories_description: `グローバル個人メモリはありません。`,
        no_server_data_title: `🟡️ サーバーデータが見つかりません`,
        no_server_data_description: `このサーバーにはデータが保存されていません。まず \`/config setup\` を実行してください。`,
        no_persona_server_memories_description: `ペルソナ「{persona_name}」にサーバーメモリはありません。`,
        no_permission_title: `🔴 権限がありません`,
        no_permission_description: `サーバーデータを削除するには**サーバー管理**権限が必要です。`,
      },
    },

    // ペルソナコマンド
    persona: {
      description: `人格プリセットを管理する`,
      name_conflict_title: `🔴 ペルソナ名の競合`,
      name_conflict_description: `**{name}** という名前のペルソナは既にこのサーバーに存在します。ペルソナ名はサーバー内で一意である必要があります。`,
      export: {
        description: `の人格を共有可能なPNGファイルとしてエクスポートする`,
        export_json_select_label: `JSONをエクスポート`,
        export_json_select_description: `任意：読み取り用JSONファイルとしてエクスポート`,
        export_json_select_placeholder: `デフォルト：いいえ（PNGでエクスポート）`,
        export_json_choice_false: `いいえ（PNGでエクスポート）`,
        export_json_choice_true: `はい（JSONでエクスポート）`,
        persona_modal_title: `ペルソナを選択`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `エクスポートするペルソナを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        success_title: `🟢 ペルソナのエクスポートに成功しました`,
        success_description: `ペルソナ **{nickname}** がエクスポートされました！このPNGファイルを他の人と共有して、人格設定を広めましょう。`,
        success_description_json: `ペルソナ **{nickname}** が読み取り用JSONファイルとしてエクスポートされました。\n\n**注意:** このJSONエクスポートは参照用のみで、インポートはできません。`,
        json_non_importable_note: `このJSONエクスポートは参照用のみで、インポートはできません。`,
        failed_title: `🔴 エクスポートに失敗しました`,
        failed_description: `ペルソナのエクスポートに失敗しました。後でもう一度お試しください。`,
        avatar_failed_title: `🔴 アバターのダウンロードに失敗しました`,
        avatar_failed_description: `ペルソナアバターのダウンロードに失敗しました。後でもう一度お試しください。`,
        embed_failed_title: `🔴 PNG処理に失敗しました`,
        embed_failed_description: `PNGファイルへのメタデータの埋め込みに失敗しました。もう一度お試しください。`,
        // Error messages from presetExport utility
        error_no_server_data: `データベースにサーバーが見つかりません。まず \`/config setup\` を実行してください。`,
        error_no_preset_data: `ペルソナデータが見つかりません。まず /config setup を実行してください。`,
        error_validation_failed: `エクスポートデータ構造の検証に失敗しました`,
        error_export_failed: `ペルソナデータのエクスポートに失敗しました`,
      },
      import: {
        description: `PNGファイルから人格をインポートする`,
        file_description: `ペルソナデータを含むPNGファイル`,
        type_description: `メインペルソナまたはオルタペルソナとしてインポート`,
        triggers_description: `任意の追加トリガー（カンマ区切り: "," または "、"）`,
        memories_description: `このペルソナの記憶（ユーザー・サーバー）を引き継ぎますか？`,
        memories_choice_preserve: `はい（ユーザー/サーバー記憶を引き継ぐ）`,
        memories_choice_fork: `いいえ（ユーザー/サーバー記憶を新しく開始する）`,
        type_choice_main: `メインペルソナ（現在の人格を置き換え）`,
        type_choice_alter: `オルタペルソナ`,
        confirmation_description: `警告：現在の人格設定が置き換えられます。続行しますか？`,
        confirmation_choice_yes: `はい、現在のペルソナを置き換えます`,
        confirmation_choice_no: `いいえ、インポートをキャンセルします`,
        success_title: `🟢 ペルソナのインポートに成功しました`,
        success_description: `ペルソナ **{nickname}** が正常にインポートされました！\n属性: {attribute_count}\nサンプル対話: {dialogue_count}\nトリガーワード: {trigger_word_count}`,
        success_confirmation: `メインペルソナ **{nickname}** が正常にインポートされました！詳細なインポート情報がチャンネルに投稿されました。`,
        nickname_update_success: `サーバーニックネームが更新されました。`,
        nickname_update_failed: `🟡 サーバーニックネームを更新できませんでした。Discordのレート制限が原因である可能性があります。手動で変更してください。`,
        avatar_update_success: `サーバーアバターが更新されました。`,
        avatar_update_rate_limited: `🟡 Discordのレート制限によりサーバーアバターは更新されませんでした。手動で変更してください。`,
        avatar_update_failed: `🟡 サーバーアバターを更新できませんでした。Discordのレート制限が原因である可能性があります。手動で変更してください。`,
        alter_success_title: `🟢 オルタペルソナのインポートに成功しました`,
        alter_success_description: `オルタペルソナ **{nickname}** が正常にインポートされました！\n固有トリガーワード: {trigger_count}\nトリガー: {triggers}\n\nこれらのトリガーがメッセージに含まれると、このペルソナが応答します。`,
        alter_success_confirmation: `オルタペルソナ **{nickname}** が {trigger_count} 個の固有トリガーワードで正常にインポートされました！詳細なインポート情報がチャンネルに投稿されました。`,
        alter_avatar_warning: `⚠️ 上記のアバター画像埋め込みを削除しないでください。削除するとオルタペルソナのアバターが失われます。`,
        alter_dm_not_allowed_title: `🔴 DMではオルタペルソナは許可されていません`,
        alter_dm_not_allowed_description: `オルタペルソナはサーバーでのみインポートできます。ダイレクトメッセージではインポートできません。サーバーでこのコマンドを実行してください。`,
        alter_no_triggers_error_title: `🔴 固有トリガーがありません`,
        alter_no_triggers_error_description: `このペルソナのすべてのトリガーワードは、他のペルソナに既に存在します。\n重複するトリガー: {overlap}\n\nPNGファイルを編集して固有のトリガーワードを追加するか、\`/persona remove\`を使用して競合するペルソナを削除してください。`,
        alter_no_triggers_warning: `⚠️ このペルソナにはトリガーワードがありません。\`/server trigger add\`を使用してトリガーを追加するまで、メッセージに応答しません。`,
        alter_name_conflict_title: `🔴 ペルソナ名が既に存在します`,
        alter_name_conflict_description: `**{name}** という名前のペルソナは既にこのサーバーに存在します。各ペルソナには固有の名前が必要です。\n\nPNGファイルを編集して別の名前を使用するか、\`/persona remove\`を使用して既存のペルソナを削除してください。`,
        alter_limit_title: `🔴 ペルソナ上限に達しました`,
        alter_limit_description: `このサーバーには既に {current} 個のペルソナがあります。上限は {max} 個です。\`/persona remove\` でオルタを削除してからインポートしてください。`,
        failed_title: `🔴 インポートに失敗しました`,
        failed_description: `ペルソナのインポートに失敗しました。ファイルを確認してもう一度お試しください。`,
        cancelled_title: `🔴 インポートがキャンセルされました`,
        cancelled_description: `インポートがキャンセルされました。私のペルソナに変更はありませんでした。`,
        invalid_file_type_title: `🔴 無効なファイル形式`,
        invalid_file_type_description: `ペルソナデータを含む有効な.pngファイルをアップロードしてください。`,
        file_too_large_title: `🔴 ファイルが大きすぎます`,
        file_too_large_description: `ファイルが大きすぎます。最大ファイルサイズは10MBです。`,
        download_failed_title: `🔴 ダウンロードに失敗しました`,
        download_failed_description: `添付ファイルのダウンロードに失敗しました。もう一度お試しください。`,
        invalid_png_title: `🔴 無効なPNGファイル`,
        invalid_png_description: `アップロードされたファイルは有効なPNG画像ではありません。`,
        no_metadata_title: `🔴 ペルソナデータが見つかりません`,
        no_metadata_description: `このPNGファイルにはペルソナデータが含まれていません。\`/persona export\`でエクスポートされたファイルを使用してください。`,
        invalid_file_title: `🔴 無効なペルソナファイル`,
        invalid_file_description: `ペルソナファイル形式が無効または互換性がありません。`,
        no_permission_title: `🔴 権限がありません`,
        no_permission_description: `ペルソナをインポートするには**サーバー管理**権限が必要です。`,
        error_download_timeout: `ファイルのダウンロードがタイムアウトしました。もう一度お試しください。`,
        error_download_failed: `ペルソナファイルのダウンロードに失敗しました。`,
        // Error messages from presetImport utility
        error_invalid_attribute: `無効な属性内容: {details}`,
        error_invalid_dialogue_in: `無効なサンプル対話(入力): {details}`,
        error_invalid_dialogue_out: `無効なサンプル対話(出力): {details}`,
        error_invalid_trigger_word: `無効なトリガーワード: {details}`,
        error_dialogue_mismatch: `サンプル対話配列の長さが一致しません`,
        error_invalid_config: `ペルソナデータに無効な設定フィールドがあります`,
        error_no_server_data: `データベースにサーバーが見つかりません。まず \`/config setup\` を実行してください。`,
        error_name_conflict: `**{name}** という名前のペルソナは既にこのサーバーに存在します。別の名前を使用してください。`,
        error_import_failed: `ペルソナデータのインポートに失敗しました`,
        error_not_json: `ペルソナファイルには有効なJSONデータが含まれている必要があります`,
        error_incompatible_version: `互換性のないペルソナバージョン。期待: {expected}、実際: {actual}`,
        error_invalid_format: `無効なペルソナファイル形式`,
        error_invalid_type: `無効なペルソナタイプ: {type}。"preset"が期待されます`,
        avatar_update_skipped_dm: `ペルソナが正常にインポートされましたが、アバターとニックネームの更新はダイレクトメッセージでは利用できません。`,
        refresh_reminder: `この会話で人格の更新を適用するには\`/tool refresh\`を実行してください`,
      },
      remove: {
        description: `サーバーからオルタペルソナを削除する`,
        confirmation_description: `確認: ペルソナ資産とペルソナ専用データのみ削除します。`,
        confirmation_choice_confirm: `削除を確定（個人のユーザー記憶は保持）`,
        confirmation_choice_cancel: `キャンセル`,
        no_permission_title: `🔴 権限がありません`,
        no_permission_description: `オルタペルソナを削除するには**サーバー管理**権限が必要です。`,
        modal_title: `オルタペルソナの削除`,
        select_label: `オルタペルソナ`,
        select_placeholder: `削除するオルタペルソナを選択...`,
        no_alters_error_title: `🟡 オルタペルソナがありません`,
        no_alters_error_description: `削除するオルタペルソナがありません。\`/persona import type:alter\`を使用してオルタペルソナをインポートしてください。`,
        success_title: `🟢 オルタペルソナを削除しました`,
        success_description: `オルタペルソナ **{nickname}** が正常に削除されました。`,
      },
      swap: {
        description: `メインペルソナとオルタペルソナを交換する`,
        no_permission_title: `🔴 権限がありません`,
        no_permission_description: `ペルソナを交換するには**サーバー管理**権限が必要です。`,
        modal_title: `メインペルソナの交換`,
        select_label: `オルタペルソナ`,
        select_placeholder: `メインに昇格させるオルタペルソナを選択...`,
        no_alters_error_title: `🟡 オルタペルソナがありません`,
        no_alters_error_description: `交換するオルタペルソナがありません。\`/persona import type:alter\`を使用してオルタペルソナをインポートしてください。`,
        success_title: `🟢 ペルソナの交換に成功しました`,
        success_description: `**{new_main}** が現在のメインペルソナになりました。\n**{old_main}** がオルタペルソナになりました。`,
        nickname_update_success: `サーバーニックネームが更新されました。`,
        nickname_update_failed: `🟡 サーバーニックネームを更新できませんでした。Discordのレート制限が原因である可能性があります。手動で変更してください。`,
        avatar_update_success: `サーバーアバターが更新されました。`,
        avatar_update_rate_limited: `🟡 Discordのレート制限によりサーバーアバターは更新されませんでした。手動で変更してください。`,
        avatar_update_failed: `🟡 サーバーアバターを更新できませんでした。Discordのレート制限が原因である可能性があります。手動で変更してください。`,
        avatar_embed_warning: `⚠️ この埋め込みを削除しないでください。削除すると保存されたアバターURLが失われる可能性があります。`,
        avatar_stored_notice: `以前のメインペルソナのアバターが保存されました。`,
      },
      default: {
        description: `人格設定のペルソナを適用します`,
        type_description: `適用先タイプ（デフォルトまたはオルタ）`,
        type_choice_default: `デフォルトペルソナ`,
        type_choice_alter: `オルタペルソナ`,
        no_permission_title: `🔴 権限がありません`,
        no_permission_description: `人格プリセットを適用するには**サーバー管理**権限が必要です。`,
        modal_title: `人格プリセットの適用`,
        select_label: `人格プリセット`,
        select_description: `適用するプリセットを選択してください。これにより、現在の属性と対話が上書きされます。`,
        select_placeholder: `プリセットを選択...`,
        no_presets_title: `利用可能なプリセットがありません`,
        no_presets_description: `あなたの言語で利用可能な人格プリセットがありません。\`/support discord\`で報告してください。`,
        preset_not_found: `選択されたプリセットが見つかりませんでした。`,
        success_title: `プリセットが適用されました`,
        success_description: `'{preset_name}'ペルソナが正常に適用されました。`,
        success_details_description: `プリセット **{preset_name}** をペルソナ **{nickname}** に適用しました！\n属性: {attribute_count}\nサンプル対話: {dialogue_count}\nトリガーワード ({trigger_word_count}): {triggers}`,
        success_confirmation: `ペルソナ **{nickname}** にプリセットを適用しました。詳細情報をこのチャンネルに投稿しました。`,
        avatar_update_failed: `🟡️ Discord APIエラーによりサーバーアバターを更新できませんでしたが、ペルソナは正常に適用されました。`,
        avatar_update_skipped_dm: `プリセットは正常に適用されましたが、アバター更新はダイレクトメッセージでは利用できません`,
      },
      generate: {
        description: `AIによる人格生成（対応プロバイダーが必要）`,
        // Modal fields
        modal: {
          title: `AI人格生成`,
          character_name_label: `キャラクター名`,
          character_name_description: `名前をカンマ（"," または "、"）区切りで入力してください。すべてトリガーワードとして追加され、先頭の名前が表示名になります。`,
          character_name_placeholder: `例: 初音ミク, ミク, Hatsune Miku`,
          character_info_label: `キャラクター情報と話し方の例`,
          character_info_description: `キャラクターとその話し方を説明してください`,
          character_info_placeholder: `性格、背景、話し方、例示のフレーズなど`,
          web_search_label: `ウェブ検索を使用しますか？`,
          web_search_description: `キャラクター情報を検索(既存メディアのキャラクター用)`,
          web_search_placeholder: `はいまたはいいえを選択`,
          web_search_yes: `はい、キャラクター情報を検索します`,
          web_search_no: `いいえ、オリジナルキャラクターを作成します`,
          additional_inst_label: `追加の指示`,
          additional_inst_placeholder: `任意：その他の指示（例：「キャラクターの返答は短くしてください」）`,
          file_upload_label: `キャラクター画像 / カード (任意)`,
          file_upload_description: `画像、Tomoriプリセット、またはSillyTavernカードPNGをアップロードして生成・変換`,
        },
        // Field labels for memory critical error preservation
        field_character_name: `キャラクター名`,
        field_character_info: `キャラクター情報と話し方の例`,
        field_web_search: `ウェブ検索を使用しますか？`,
        field_additional_inst: `追加の指示`,
        // Error messages
        wrong_provider_title: `🔴 互換性のないプロバイダー`,
        wrong_provider_description: `ペルソナ生成には対応プロバイダーが必要です。現在のプロバイダーは **{current_provider}** です。\`/config apikey set\`を使用してプロバイダーを切り替えてください。`,
        no_api_key_title: `🔴 APIキーがありません`,
        no_api_key_description: `APIキーが設定されていません。\`/config apikey set\`を使用してプロバイダーのAPIキーを設定してください。`,
        model_incompatible_title: `互換性のないモデル`,
        model_incompatible_description: `現在のモデル（**{model_name}**）は、ペルソナ生成に必要な**構造化出力**をサポートしていません。\n\n**次のステップ:**\n\`/config model text\`を使用して、構造化出力をサポートするモデル（例：「STRUCT」機能を持つモデル）に切り替えてください。`,
        image_vision_required_title: `🔴 画像ビジョンが必要`,
        image_vision_required_description: `画像がアップロードされましたが、現在のモデル（**{model_name}**）は**画像ビジョン**をサポートしておらず、ビジョンモデルも設定されていません。\n\n**次のステップ:**\n1. \`/config model vision\`を使用して専用ビジョンモデルを設定する、または\n2. \`/config model text\`を使用してビジョン対応モデルに切り替える、または\n3. 画像を削除して画像なしで再生成する`,
        vision_model_provider_unsupported_title: `🔴 ビジョンモデルのプロバイダー非対応`,
        vision_model_provider_unsupported_description: `ビジョンモデル（**{vision_model_name}**）はプロバイダー **{vision_provider}** に設定されていますが、このプロバイダーはペルソナプリセット生成に対応していません。\n\n**次のステップ:**\n1. \`/config model vision\`を使用して対応プロバイダー（Google、OpenRouter、DeepSeek、Z.ai、Custom、NVIDIA NIM）のビジョンモデルを設定する、または\n2. \`/config model text\`を使用してビジョンとプリセット生成の両方に対応したプライマリモデルに切り替える`,
        web_search_tools_required_title: `🔴 ウェブ検索を利用できません`,
        web_search_tools_required_description: `ウェブ検索が選択されましたが、現在のモデル（**{model_name}**）は**ツール**に対応していません。\n\n**次のステップ:**\n1. \`/config model text\`を使用してツール対応モデルに切り替える、または\n2. ウェブ検索なしで再生成する（質問されたら「いいえ」を選択）`,
        api_key_decrypt_failed_title: `🔴 APIキーエラー`,
        api_key_decrypt_failed_description: `APIキーの復号化に失敗しました。\`/config apikey set\`を使用して再設定してください。`,
        invalid_image_title: `🔴 無効な画像`,
        invalid_image_description: `有効な画像ファイル(PNG、JPG、JPEGなど)をアップロードしてください。`,
        image_download_failed_title: `🔴 画像のダウンロードに失敗しました`,
        image_download_failed_description: `添付画像のダウンロードに失敗しました。もう一度お試しください。`,
        error_file_too_large: `アバター画像は8MB以下である必要があります。`,
        error_download_timeout: `アバターのダウンロードがタイムアウトしました。もう一度お試しください。`,
        error_download_failed: `アバター画像のダウンロードに失敗しました。`,
        // Processing
        processing_title: `人格を生成しています...`,
        processing_description: `これには1～2分かかる場合があります。キャラクターを生成していますので、お待ちください...\n\nこれは予期しない結果が生成される場合があります。必要に応じて再生成できます。`,
        // Generation errors
        generation_failed_title: `🔴 生成に失敗しました`,
        generation_failed_description: `人格の生成に失敗しました：{error}\n\n異なる入力で再度お試しいただくか、APIキーを確認してください。`,
        validation_failed_title: `🔴 検証に失敗しました`,
        validation_failed_description: `生成された人格データの検証に失敗しました。もう一度お試しください。`,
        image_processing_failed_title: `🔴 画像処理に失敗しました`,
        image_processing_failed_description: `アップロードされた画像の処理に失敗しました。別の画像をお試しください。`,
        avatar_fetch_failed_title: `🔴 アバターの取得に失敗しました`,
        avatar_fetch_failed_description: `エクスポート用のサーバーアバターの取得に失敗しました。代わりに画像をアップロードしてみてください。`,
        metadata_embed_failed_title: `🔴 エクスポートに失敗しました`,
        metadata_embed_failed_description: `画像に人格データを埋め込むことができませんでした。もう一度お試しください。`,
        // Success
        success_title: `🟢 {character_name} の生成に成功しました！`,
        success_description: `**{character_name}** の人格を生成しました！\n**属性プレビュー:**\n{attribute_preview}\n**サンプル対話:**\n{dialogue_preview}`,
        success_next_steps_title: `次のステップ`,
        success_next_steps_description: `1. 添付されたPNGファイルをダウンロード\n2. PNGファイルと共に\`/persona import\`を使用してこのキャラクターをインポート\n3. 進行中の会話に新しい人格を適用するには\`/tool refresh\`を実行\n4. (任意) 必要に応じて\`/server avatar\`でアバターを変更`,
        avatar_update_skipped_dm: `アバターとニックネームの更新はダイレクトメッセージでインポートできませんのでご注意ください。`,
      },
      create: {
        description: `シンプルな人格プリセットを手動で作成`,
        // Modal fields
        modal: {
          title: `ペルソナ作成`,
          character_name_label: `キャラクター名`,
          character_name_description: `名前をカンマ（"," または "、"）区切りで入力してください。すべてトリガーワードとして追加され、先頭の名前が表示名になります。`,
          character_name_placeholder: `例: 初音ミク, ミク, Hatsune Miku`,
          character_desc_label: `キャラクター説明`,
          character_desc_placeholder: `キャラクターを説明してください（性格、外見、背景など）`,
          example_user_label: `ユーザーメッセージの例`,
          example_user_description: `ヒント: インポート後に /teach sampledialogue で例を追加できます`,
          example_user_placeholder: `こんにちは、{bot}！`,
          example_bot_label: `ボット返信の例`,
          example_bot_placeholder: `こんにちは、{user}！お元気ですか？`,
          file_upload_label: `キャラクター画像 (任意)`,
          file_upload_description: `キャラクターエクスポート用の画像をアップロード`,
        },
        // Field labels for memory critical error preservation
        field_character_name: `キャラクター名`,
        field_character_desc: `キャラクター説明`,
        field_example_user: `ユーザーメッセージの例`,
        field_example_bot: `ボット返信の例`,
        // Error messages
        invalid_image_title: `🔴 無効な画像`,
        invalid_image_description: `有効な画像ファイル(PNG、JPG、JPEGなど)をアップロードしてください。`,
        image_download_failed_title: `🔴 画像のダウンロードに失敗しました`,
        image_download_failed_description: `添付画像のダウンロードに失敗しました。もう一度お試しください。`,
        error_file_too_large: `アバター画像は8MB以下である必要があります。`,
        error_download_timeout: `アバターのダウンロードがタイムアウトしました。もう一度お試しください。`,
        error_download_failed: `アバター画像のダウンロードに失敗しました。`,

        desc_too_long_title: `説明が長すぎます`,
        desc_too_long_description: `キャラクターの説明が長すぎます（{current_length} 文字）。最大許容長は {max_allowed} 文字です。`,
        example_user_too_long_title: `ユーザーメッセージの例が長すぎます`,
        example_user_too_long_description: `ユーザーメッセージの例が長すぎます（{current_length} 文字）。最大許容長は {max_allowed} 文字です。`,
        example_bot_too_long_title: `ボット返信の例が長すぎます`,
        example_bot_too_long_description: `ボット返信の例が長すぎます（{current_length} 文字）。最大許容長は {max_allowed} 文字です。`,

        validation_failed_title: `🔴 検証に失敗しました`,
        validation_failed_description: `ペルソナデータの検証に失敗しました。もう一度お試しください。`,
        image_processing_failed_title: `🔴 画像処理に失敗しました`,
        image_processing_failed_description: `アップロードされた画像の処理に失敗しました。別の画像をお試しください。`,
        avatar_fetch_failed_title: `🔴 アバターの取得に失敗しました`,
        avatar_fetch_failed_description: `エクスポート用のサーバーアバターの取得に失敗しました。代わりに画像をアップロードしてみてください。`,
        metadata_embed_failed_title: `🔴 エクスポートに失敗しました`,
        metadata_embed_failed_description: `画像に人格データを埋め込むことができませんでした。もう一度お試しください。`,
        // Success
        success_title: `🟢 {character_name} の作成に成功しました！`,
        success_description: `**{character_name}** のペルソナが作成されました！\n**説明:**\n{character_description}`,
        success_dialogue_title: `サンプル対話`,
        success_next_steps_title: `次のステップ`,
        success_next_steps_description: `1. 添付されたPNGファイルをダウンロード\n2. PNGファイルと共に\`/persona import\`を使用してこのキャラクターをインポート\n3. 進行中の会話に新しい人格を適用するには\`/tool refresh\`を実行\n4. (任意) 必要に応じて\`/server avatar\`でアバターを変更`,
        avatar_update_skipped_dm: `アバターとニックネームの更新はダイレクトメッセージでは利用できませんのでご注意ください。`,
      },
    },

    // ヘルプコマンド
    help: {
      // /help features
      features: {
        description: `TomoriBotができることを表示`,
        title: `TomoriBotの機能（バージョン {version}）`,
        embed_description: `これが私の全機能です：`,
        vision_title: `ビジョン＆メディア`,
        vision_description: `- 画像、動画、スタンプ、絵文字を見て分析できます
- YouTubeリンクから動画を視聴できます
- 共有された埋め込み（ツイート、記事など）の内容を見ることができます`,
        search_title: `検索＆情報 `,
        search_description: `- 最新情報をウェブ検索できます
- 画像、動画、ニュース検索も可能です（\`/optionalkey brave set\`経由）
- URLからコンテンツを取得して読むことができます`,
        personality_title: `パーソナリティ＆カスタマイズ`,
        personality_description: `- \`/config rename\`と\`/server avatar\`で名前とアバターを変更できます
- \`/persona\`で異なるペルソナに切り替えられます（\`/persona export\`でペルソナを共有・保存もできます！）
- アルターペルソナとして複数のキャラクターが同一サーバーで共存し、それぞれ独自のトリガーとウェブフックアバターを持てます
- \`/teach\`で行動やトーンを調整できます
- \`/config sysprompt\`でカスタムシステムプロンプトを設定し、行動をさらに形張ることができます
- 詳しくは\`/help customization\`をご覧ください`,
        memory_title: `記憶＆パーソナライゼーション`,
        memory_description: `- ユーザーやサーバーに関する事実を記憶し、会話を跨いで保持します
- 個人的な記憶は全サーバーで保持されます（他のサーバーでも私に話しかけてみて！）
- 最近の会話はSTM（短期記憶）として保持し、チャンネルやサーバーをまたいで文脈を把握します（クロスサーバー共有は\`/personal stm\`でオプトインできます）
- \`/personal nickname\`であなたを呼ぶ名前を変更できます
- \`/teach\`で手動で記憶させ、\`/forget\`で削除できます
- \`/server initialize expressions\`で絵文字やステッカーを登録すると、より適切な場面で使えるようになります
- \`/personal privacy\`で完全に見えなくなるオプションが利用可能です
- 詳しくは\`/help memory\`をご覧ください`,
        time_title: `時間認識`,
        time_description: `- サーバーの現在時刻を認識しています（\`/config timezone\`経由）
- リマインダーを設定できます（何かを思い出させるように頼んでみて！）
- 繰り返しリマインダーもサポートされており、ペルソナ固有です`,
        alter_title: `アルターペルソナ`,
        alter_description: `- アルターペルソナを使って、一つのサーバーに複数のキャラクターが共存できます
- それぞれのアルターは独自のパーソナリティを持ち、特定のキーワードでトリガーされます
- アルターペルソナは異なるアバターのためにウェブフックを使用します
- 一つのメッセージで複数のアルターを同時にトリガーできます（\`/config multitrigger\`の上限まで）
- ウェブフックメッセージに返信すると、そのペルソナとして会話が続きます
- \`/persona import\`（アルターオプション）と\`/persona remove\`でアルターを管理できます`,
        expressions_title: `表情＆リアクション`,
        expressions_description: `- サーバーのカスタム絵文字を会話で自然に使えます（大文字小文字不問の \`:名前:\` 形式）
- 返信の一部としてスタンプを送れます
- 関連する絵文字でメッセージにリアクションできます
- \`/server initialize expressions\`で絵文字とスタンプを登録すると精度が向上します`,
        documents_title: `ドキュメント知識庫`,
        documents_description: `- \`/teach document\`でテキスト、PDF、Markdownファイルをサーバー知識としてアップロードできます
- 質問に答える際に、私は関連するドキュメント内容を取得して参照します
- チャットで共有されたドキュメント添付ファイル（PDF、TXT、MD）も直接読み取れます、読んでと頼むだけ！
- 埋め込みモデルが必要です（\`/config model embedding\`で設定）
- \`/forget document\`でドキュメントを削除できます`,
        impersonation_title: `なりきり＆ツール`,
        impersonation_description: `- \`/bot impersonate\`で自分自身、ペルソナ、またはシステムメッセージとしてメッセージを送信できます
- \`/personal impersonate prompt\`でユーザーなりすまし用の再利用プロンプトを設定できます
- \`/tools compact\`で会話履歴を要約したりロールプレイで圧縮できます
- \`/reward\`コマンド（headpat、hug、kiss、tickle）でインタラクティブなご褒美モーメント`,
        imagegen_title: `画像生成`,
        imagegen_description: `- テキストプロンプトから画像を生成し、参照画像を編集することもできます
- Text2ImageとImage2Imageをカスタマイズタブルなアスペクト比で対応
- \`/generate image\`を使うか、画像を生成してほしいと頼むだけで動作します
- 参照画像としてメッセージの添付ファイル、ステッカー、絵文字、ユーザーアバターを使えます
- Google、OpenRouter、Z.ai、Z.ai (Coding)、NVIDIA NIMプロバイダーで利用可能（\`/config model image\`で設定）`,
        footer: `すべての機能がすべてのAIプロバイダーで利用できるわけではありません。推奨：Google Gemini。私に直接何ができるか聞いてみることもできます！`,
      },

      // /help cost
      cost: {
        description: `有料AIプロバイダーのAPI費用を見積もる`,
        title: `推定API費用`,
        embed_description: `Discordチャンネルでのトリガーあたりの**非常におおまかな**推定費用です。費用は**{provider}**の例を使用して推定されています（入力：{inputPrice}/百万トークン、出力：{outputPrice}/百万トークン）`,
        current_context_description: `あなたの**現在のコンテキストのみ**を対象にした推定費用です。入力トークンは、現在の設定と直近のチャンネル履歴を使って、**{provider}** のモデル **{model}** でプロバイダーAPI計測を行います。出力トークンは推定値です。使用価格: 入力 {inputPrice}/百万、出力 {outputPrice}/百万。`,
        current_input_title: `計測済み入力トークン（現在のコンテキスト）`,
        current_input_value: `**入力:** {inputTokens} トークン\n**入力コストのみ:** 1トリガーあたり約 {inputCost}`,
        current_output_short_title: `推定出力: 短め`,
        current_output_typical_title: `推定出力: 標準`,
        current_output_long_title: `推定出力: 長め`,
        current_output_band_value: `**出力推定:** {outputTokens} トークン\n**合計推定:** {totalTokens} トークン\n**費用:** 1トリガーあたり約 {costPerMessage}（100トリガーあたり約 {costPer100}）`,
        current_footer: `入力トークンは、ライブ計測に対応したプロバイダーでのみプロバイダー計測値になります。出力トークンは推定値です。`,
        fallback_notice_title: `ライブ計測を利用できません`,
        fallback_notice_value: `現在の設定ではライブのプロバイダートークン計測を利用できなかったため、この表示はおおまかな代替推定です。`,
        minimum_scenario_title: `最小シナリオ（軽量使用）`,
        minimum_scenario_value: `**コンテキスト：** 1ユーザー、メモリなし、1段落のペルソナ、会話は1メッセージあたり1文未満
**トークン数：** {inputTokens} 入力 + {outputTokens} 出力 = {totalTokens} 合計
**費用：** ~{costPerMessage} /トリガー（~{costPer100} /100トリガー）`,
        average_scenario_title: `平均シナリオ（中程度使用）`,
        average_scenario_value: `**コンテキスト：** 3ユーザー（各10メモリ）、~16段落のペルソナ（属性と対話を含む）、会話は1メッセージあたり1〜2文
**トークン数：** {inputTokens} 入力 + {outputTokens} 出力 = {totalTokens} 合計
**費用：** ~{costPerMessage} /トリガー（~{costPer100} /100トリガー）`,
        maximum_scenario_title: `最大シナリオ（重量使用）`,
        maximum_scenario_value: `**コンテキスト：** 5ユーザー（各25メモリ）、~31段落のペルソナ（属性と対話を含む）、会話は1メッセージあたり2段落
**トークン数：** {inputTokens} 入力 + {outputTokens} 出力 = {totalTokens} 合計
**費用：** ~{costPerMessage} /トリガー（~{costPer100} /100トリガー）`,
        breakdown_title: `費用に影響する要因`,
        breakdown_value: `**入力トークン（AIに送信されるコンテキスト）：**
- ペルソナの段落数（属性とサンプル対話を含む）
- サーバー＆個人メモリ
- 有効化されたツール（ある場合）
- ユーザーステータス＆リマインダー
- 最近の会話履歴（プロバイダーがサポートしている場合、画像、動画、スタンプ、絵文字、埋め込みを含む）
- サーバー絵文字（常に10個）

**出力トークン（AI応答）：**
- 応答の長さはクエリの複雑さによって異なります
- より詳細な質問 = より長い応答 = より高い費用

**費用を削減するヒント：**
サーバー内の悪用者やスパマーによる費用を削減するための組み込み機能がありますが、以下の追加のヒントもあります：
- ペルソナの段落数を少なくする（属性と対話）
- メモリを簡潔に保つ
- 無料のAIプロバイダーを使用する（Google Gemini無料プラン）
- 自動トリガーチャンネルを制限する`,
        footer: `Google Gemini（無料プラン）や一部のOpenRouterモデルなどの無料プロバイダーは費用がかかりません！NovelAIはサブスクリプション制で無制限に使用できます。プロバイダーの詳細は\`/help apikey\`をご覧ください。`,
      },

      // /help setup
      setup: {
        description: `TomoriBotの初期設定方法を学ぶ`,
        title: `TomoriBotを始める`,
        embed_description: `サーバー（またはDM）でTomoriBotを設定する方法：`,
        step1_title: `ステップ1：APIキーを取得`,
        step1_description: `TomoriBotはGoogle Gemini、NovelAI、OpenRouterなどのAIプロバイダーを使用します。いずれかのAPIキーが必要です。
- {helpApikey}で取得方法を確認
  - GoogleのGemini = 汎用、無料、すべての機能を実行可能
  - NovelAI = 無検閲なロールプレイとストーリーテリング特化
  - OpenRouter = 様々なAIモデルが利用可能
- このAPIキーを**他人と共有しないでください**`,
        step2_title: `ステップ2：セットアップコマンドを実行`,
        step2_description: `- {configSetup}を使用してAPIキーを安全に追加し、TomoriBotを初期化
- （推奨）{serverInitializeExpressions}を実行して、サーバーの絵文字/スタンプ表現を適切に使えるようにする
	- APIキーは暗号化されて安全に保存されます
	- 各サーバーには独自の設定があります`,
        step3_title: `ステップ3：チャットを始める！`,
        step3_description: `- メンションするか、私のメッセージに返信するだけでチャットできます
- {serverTrigger}でトリガー方法を変更できます
- 記憶システムで会話を記憶します（{configPermissions}で無効化できます！）
- {serverAutotrigger}で自動トリガーを設定し、メンションなしでチャットできます`,
        step4_title: `オプション：カスタマイズする`,
        step4_description: `- {persona}コマンドで私のパーソナリティを完全に変更（アルターペルソナも含む！）
- {server}、{personal}、{config}コマンドで設定を調整
- {teach}で手動で物事を教えることもできます
- ドキュメントアップロード、APIキーローテーション、検閲なしモードなどの高度な機能も探してみてください`,
        need_help_title: `ヘルプが必要ですか？`,
        need_help_description: `- {helpFeatures} - 私ができることを見る
- {helpMemory} - 記憶システムについて学ぶ
- {helpCustomization} - パーソナリティのカスタマイズについて学ぶ
- {supportServer} - 公式TomoriBotサポートサーバーに参加

TomoriBotをセットアップすることで、あなたとサーバーメンバーは\`/legal terms\`と\`/legal privacy\`の通知に同意したことになります`,
      },

      // /help matrix
      matrix: {
        description: `Matrixブリッジの設定方法と使い方を学ぶ`,
        title: `Matrixブリッジガイド`,
        embed_description: `MatrixルームをDiscordチャンネルにリンクする方法と、現在Matrix側で使える機能の案内です。`,
        bot_user_fallback: `設定されているMatrixボットアカウント`,
        setup_title: `セットアップ`,
        setup_description: `1. 暗号化されていないMatrixルームに {botUserId} を招待します。
2. そのルームの Internal Room ID を確認します。
3. ブリッジしたいDiscordチャンネルで {serverMatrixLink} を実行し、そのルームIDを貼り付けます。`,
        room_id_title: `ルームIDの確認方法`,
        room_id_description: `多くのMatrixクライアントでは Room Settings -> Advanced -> Internal Room ID から確認できます。
IDの形式は \`!abc:matrix.org\` のようになります。

ボットが招待を受け入れると、Matrixルームにも短い案内を送りますが、リンク完了には引き続きDiscord側で {serverMatrixLink} を実行する必要があります。`,
        usage_title: `Matrixからの使い方`,
        usage_description: `- ルームをリンクした後は、Matrixで普通に話しかければ使えます
- Matrixのメッセージはリンク先のDiscordチャンネルにWebhookとして転送されます
- TomoriBotの返信はMatrixルームにも戻ってきます
- Matrix側で使えるテキストコマンドは /kill と /refresh のみです`,
        limitations_title: `現在の制限`,
        limitations_description: `- MatrixからSlash Commandは使えません
- DM / DM経由のクールダウン通知は使えません
- Matrixユーザーのプロフィール画像はTomoriBotから見えません
- メッセージのピン留めはできません
- カスタム絵文字やMarkdownは安定して描画されません
- Embedはプレーンテキストとして転送されます
- Matrixユーザーの個人メモリは属性付きのサーバーメモリにフォールバックします`,
        troubleshooting_title: `注意事項`,
        troubleshooting_description: `- ボットが自動参加しない場合は {botUserId} を手動で招待し、必要なら {serverMatrixLink} を再実行してください
- Matrixの暗号化は後から無効化できないため、暗号化済みルームは使えず、新しい非暗号化ルームが必要です
- 上に書かれていない制限は基本的に動作する想定なので、動かない場合は {supportServer} で報告してください`,
      },

      // /help data
      data: {
        description: `データ管理とプライバシーについて学ぶ`,
        title: `データの管理`,
        embed_description: `データの管理方法と保存内容：`,
        export_title: `データのエクスポート`,
        export_description: `{dataExport}を使用してデータをダウンロード：
- **ペルソナの個人メモリ**
- **ペルソナのサーバーメモリ**
- **個人設定**
- **サーバー設定**
- **グローバル個人メモリ**
- データはJSONファイルとしてDMに送信されます`,
        import_title: `データのインポート`,
        import_description: `{dataImport}を使用してエクスポートしたデータを復元：
- エクスポートファイルの種類を自動判別します
- メモリ系ファイルは「ペルソナ」または「グローバル」適用先を選択します
- サーバー系インポートにはサーバー管理権限が必要です
- コマンド使用時にエクスポートしたファイルを添付するだけ`,
        delete_title: `データの削除`,
        delete_description: `{dataDelete}を使用してデータを完全に削除：
- **ペルソナの個人メモリ** / **グローバル個人メモリ**
- **ペルソナのサーバーメモリ**
- **個人設定** / **サーバー設定のリセット**
- この操作は元に戻せません！`,
        privacy_title: `プライバシー通知`,
        privacy_description: `**保存するもの：**
- サーバー/個人の記憶
- 私の設定とペルソナ
- 私のサーバー設定
- 暗号化されたAPIキー

**保存しないもの：**
- Discordメッセージ
- チャット履歴

**選択したAIプロバイダーに送信されるもの：**
トリガーされるたびに、AIモデルが返信を形成するためのコンテキストとして、テキストチャンネルの**最新メッセージ**と**関連する記憶**を取得します。これらのトリガー以外でメッセージを積極的に監視したり閲覧したりすることはありません。

{personalPrivacy}コマンドで記憶機能をオプトアウトし、{configPermissions}コマンドで自己学習を無効化できます。`,
        footer: `選択したAIプロバイダー（Google、NovelAI、OpenRouter）は独自のプライバシーポリシーに従ってメッセージを処理します。プライバシーのため、個人情報を共有しないでください。詳細は\`/legal privacy\`と\`/legal terms\`をご覧ください`,
      },

      // /help apikey
      apikey: {
        description: `AIプロバイダーのAPIキー設定方法を学ぶ`,
        provider_description: `AIプロバイダーを選択`,
        provider_choice_brave: `Brave Search`,
        provider_choice_google: `Google Gemini`,
        provider_choice_deepseek: `DeepSeek`,
        provider_choice_nvidia: `NVIDIA NIM`,
        provider_choice_novelai: `NovelAI`,
        provider_choice_openrouter: `OpenRouter`,
        // Brave Search
        brave_title: `Brave Search APIキーの設定`,
        brave_description: `Brave Searchはオプションで、検索機能を強化するだけです。これは私のAIを動かすものではありません（それはメインプロバイダーが担当します）。
- 画像、動画、ニュース検索を有効化
- インターネットからリアルタイム情報を提供
- 最新の質問に答える能力を強化
- 無料プランには月2,000クエリが含まれます`,
        brave_getting_key_title: `APIキーの取得：`,
        brave_getting_key_description: `1. [Brave Search API](https://brave.com/search/api/)にアクセス
2. 無料アカウントに登録
3. ダッシュボードの[APIキー](https://api-dashboard.search.brave.com/app/keys)セクションに移動
4. 新しいAPIキーを作成
5. {configBraveapiSet}コマンドでAPIキーをコピーして入力`,
        brave_important_title: `重要な注意事項：`,
        brave_important_description: `- これはメインAIプロバイダーとは別です
- Brave APIキーがなくても、組み込みウェブ検索で機能します`,
        brave_footer: `メインAIプロバイダーの設定については、他の\`/help apikey\`オプションを確認してください`,
        // Google Gemini
        google_title: `Google Gemini APIキーの設定`,
        google_description: `Google Geminiは強力なAIモデルを備えた無料および有料プランを提供します。
- 無料プランで十分な制限あり
- ビジョンやペルソナ生成などTomoriBotの全機能をサポート
- [Geminiプライバシーポリシー](https://ai.google.dev/gemini-api/terms)`,
        google_getting_key_title: `APIキーの取得：`,
        google_getting_key_description: `1. [Google AI Studio](https://aistudio.google.com/apikey)にアクセス
2. 右上の\`APIキーを作成\`をクリック（必要に応じて新しいプロジェクトを作成）
3. このAPIキーを{configSetup}または{configApikeySet}にコピー`,
        google_footer: `このプロバイダーを設定したら、{configModel}でデフォルトモデルを変更できます`,
        // DeepSeek
        deepseek_title: `DeepSeek APIキーの設定`,
        deepseek_description: `DeepSeekは従量課金制で、自社のチャットモデルと推論モデルへ直接アクセスできます。
- TomoriBotではDeepSeekのチャットモデルと推論モデルを利用できます
- TomoriBotではツール対応および構造化出力対応のテキストモデルを利用できます
- TomoriBotのDeepSeekプロバイダーでは、ネイティブ画像生成と埋め込みは現在利用できません
- [DeepSeek APIドキュメント](https://api-docs.deepseek.com/)`,
        deepseek_getting_key_title: `APIキーの取得：`,
        deepseek_getting_key_description: `1. [DeepSeek API Keys](https://platform.deepseek.com/api_keys)にアクセス
2. DeepSeekのプラットフォームアカウントにログイン、または新規作成
3. 新しいAPIキーを作成
4. 必要に応じて、使用前にDeepSeekプラットフォームアカウントへ残高を追加
5. このAPIキーを{configSetup}または{configApikeySet}にコピー`,
        deepseek_model_notes_title: `モデルに関するメモ：`,
        deepseek_model_notes_description: `- \`deepseek-chat\` は汎用チャットモデルです
- \`deepseek-reasoner\` はシンキング／推論モデルで、応答が遅くなる場合があります
- セットアップ後は利用可能なDeepSeekテキストモデル間で切り替えられます`,
        deepseek_footer: `このプロバイダーを設定したら、{configModel}でデフォルトモデルを変更できます`,
        // NVIDIA NIM
        nvidia_title: `NVIDIA NIM APIキーの設定`,
        nvidia_description: `NVIDIA NIMは、NVIDIAのAPIカタログを通じてホスト型のチャット、埋め込み、画像生成を提供します。
- チャットと埋め込みは、NVIDIAのホスト型 \`integrate.api.nvidia.com\` を使用します
- ネイティブ画像生成は、NVIDIAホストの \`ai.api.nvidia.com\` Stabilityエンドポイントを使用します
- 構造化出力と履歴抽出は、対応するNVIDIAテキストモデルでのみ利用できます`,
        nvidia_getting_key_title: `APIキーの取得：`,
        nvidia_getting_key_description: `1. [NVIDIA Build](https://build.nvidia.com/)にアクセス
2. NVIDIA開発者アカウントでログイン、または新規作成
3. [API Keysページ](https://build.nvidia.com/settings/api-keys)でAPIキーを作成または管理
4. このAPIキーを{configSetup}または{configApikeySet}にコピー`,
        nvidia_model_notes_title: `モデルに関するメモ：`,
        nvidia_model_notes_description: `- \`deepseek-ai/deepseek-v3.2\` はデフォルトの汎用チャットモデルです
- \`qwen/qwen3.5-397b-a17b\` はTomoriBotの厳選NVIDIAセット内で最も高性能なマルチモーダルモデルです
- \`nv-embed-v1\` はデフォルトの埋め込みモデルです
- \`stabilityai/stable-diffusion-3-medium\` はデフォルトのNVIDIA画像モデルです`,
        nvidia_footer: `このプロバイダーを設定したら、{configModel}、{configModelEmbedding}、{configModelImage}でテキスト・埋め込み・画像モデルを変更できます`,
        // Z.ai
        provider_choice_zai: `Z.ai`,
        provider_choice_zaicoding: `Z.ai (Coding)`,
        provider_choice_vertex: `Google Vertex AI`,
        provider_choice_elevenlabs: `ElevenLabs TTS`,
        zai_title: `Z.ai APIキーの設定`,
        zai_description: `Z.aiはGLMモデルファミリーへのアクセスを提供し、汎用APIと専用Codingエンドポイントの両方に対応しています。
- チャット、推論、画像生成、コーディングワークフローをサポート
- ビジョンや推論バリアントを含むGLMモデルを使用
- \`glm-image\`によるネイティブ画像生成
- すべてのチャットモデルでツール呼び出しと構造化出力に対応
- 追加の画像/動画ワークフロー向けに\`/config mcp add\`で任意のMCPアドオンを利用可能`,
        zai_general_endpoint_title: `汎用APIエンドポイント：`,
        zai_general_endpoint_description: `汎用Z.aiエンドポイントはチャット、推論、画像生成へのアクセスを提供します。
- 一般的なAI利用と幅広い互換性に最適
- ビジョンや推論機能を持つすべてのGLMチャットモデルに対応`,
        zai_coding_endpoint_title: `Codingエンドポイント：`,
        zai_coding_endpoint_description: `専用のCodingエンドポイントはGLM Coding PlanとコーディングツールワークフローにGLM向けに最適化されています。
- 一般的なAPI利用ではなくコーディング用途を想定
- 異なる課金体系とアクセスパターンを持つ専用エンドポイントを使用
- 標準課金の通常APIや幅広い一般用途が必要な場合は汎用エンドポイントをご利用ください`,
        zai_getting_key_title: `APIキーの取得：`,
        zai_getting_key_description: `1. [Z.aiプラットフォーム](https://z.ai)にアクセス
2. ログインまたはアカウントを作成
3. ダッシュボードでAPIキーに移動
4. 新しいAPIキーを作成
5. このAPIキーを{configSetup}または{configApikeySet}にコピー`,
        zai_model_notes_title: `モデルに関するメモ：`,
        zai_model_notes_description: `- \`glm-5\` は高度な推論を備えた最も高性能なモデルです
- \`glm-4.7\` は推論/シンキングモードをサポートします
- \`glm-4.7-flash\` は高速で無料のモデルです
- \`glm-4.6v\` は画像を見ることができるビジョン対応モデルです
- \`glm-image\` はテキストプロンプトから画像を生成します`,
        zai_footer: `このプロバイダーを設定したら、{configModel}でデフォルトモデルを変更できます`,
        // NovelAI
        novelai_title: `NovelAI APIキーの設定`,
        novelai_description: `NovelAIはクリエイティブなストーリーテリングとロールプレイに焦点を当てたサブスクリプションベースのサービスです。
- 無制限の無検閲メッセージ
- 現在、テキスト生成のみをサポートしています（ビジョンやアシスタント機能はありません）。
- [NovelAI利用規約](https://novelai.net/terms)`,
        novelai_getting_key_title: `APIキーの取得：`,
        novelai_getting_key_description: `1. [NovelAI](https://novelai.net/stories)にアクセス
2. 左上の⚙️アイコンから設定に移動
3. \`アカウント\`に移動
4. \`永続的APIトークンを取得\`を探す（購読申し込みが必要です！）
5. このAPIキーを{configSetup}または{configApikeySet}にコピー`,
        novelai_footer: `このプロバイダーを設定したら、{configModel}でデフォルトモデルを変更できます`,
        // OpenRouter
        openrouter_title: `OpenRouter APIキーの設定`,
        openrouter_description: `OpenRouterは従量課金制で複数のプロバイダーの様々なAIモデルへのアクセスを提供します。
- 最新かつ最も強力なAIモデルへのアクセス（無料もあります）
- 現在、TomoriBotの全機能をサポートしていません
- [OpenRouter利用規約](https://openrouter.ai/terms)`,
        openrouter_getting_key_title: `APIキーの取得：`,
        openrouter_getting_key_description: `1. [OpenRouter](https://openrouter.ai/settings/keys)にアクセス
2. \`APIキーを作成\`をクリック
3. このAPIキーを{configSetup}または{configApikeySet}にコピー`,
        openrouter_model_selection_title: `モデルの選択：`,
        openrouter_model_selection_description: `OpenRouterは多くの異なるAIモデルへのアクセスを提供します。
	- 現在利用可能なモデルは人気と性能に基づいており、区別のためのタグが付いています：
	  - (TOOLS) = ツール使用をサポート（ウェブ検索、自己学習、ステッカーなど）
	  - (IMG) = 画像を認識
	  - (VID) = 動画を認識
	  - (STRUCT) = 構造化出力をサポート（ペルソナ生成や表情の初期化に必要）
	  - (REASON) = 推論／シンキング特化モデル
	  - (FREE) = 無料ですが、レート制限がある場合があります
	- 希望のモデルが見つからない場合は、\`other-model\`プロバイダーオプションを試してみてください
	- {supportServer}で追加のモデルを提案してください`,
        openrouter_pricing_title: `重要な価格に関する注意事項：`,
        openrouter_pricing_description: `- **無料モデルは厳格なレート制限があります** - より信頼性の高い有料モデルをお勧めします
- 予期しないコストを避けるため、モデルを選択する前に**OpenRouterで必ず価格を確認してください**
- モデルによってコストが大きく異なります`,
        openrouter_settings_title: `OpenRouterアカウント設定：`,
        openrouter_settings_description: `OpenRouterアカウントで設定された設定（モデルの優先順位、レート制限など）は、TomoriBotを使用する際にも適用されます`,
        openrouter_footer: `このプロバイダーを設定したら、{configModel}でデフォルトモデルを変更できます`,
        // Vertex AI
        vertex_title: `Google Vertex AIの設定`,
        vertex_description: `Google Vertex AIは、Google Cloudを通じてGeminiモデルへのエンタープライズグレードのアクセスを提供します。
- 認証にApplication Default Credentials（ADC）を使用 — APIキーの管理が不要
- チャット、ツール呼び出し、ストリーミング、構造化出力、圧縮、埋め込み、プリセット生成に対応
- BotがGCP IDで実行されるセルフホストまたは信頼できる環境に最適
- [Vertex AIドキュメント](https://cloud.google.com/vertex-ai/docs)`,
        vertex_getting_key_title: `設定手順：`,
        vertex_getting_key_description: `1. Vertex AI APIが有効なGoogle Cloudプロジェクトを用意
2. ホストマシンでApplication Default Credentialsを設定：
   - **サービスアカウント**：Vertex AIアクセス権を持つサービスアカウントをVM/コンテナにアタッチ
   - **ローカル開発**：\`gcloud auth application-default login\`を実行
   - **環境変数**：\`GOOGLE_APPLICATION_CREDENTIALS\`にサービスアカウントキーファイルのパスを設定
3. {configSetup}または{configApikeySet}で\`{project_id}::{location}\`の形式で設定
   - 例：\`my-gcp-project::us-central1\``,
        vertex_important_title: `重要な注意事項：`,
        vertex_important_description: `- 保存される値は**設定情報**（プロジェクト＋ロケーション）であり、認証情報ではありません
- すべてのVertexリクエストはホストのADC IDを使用 — サーバーごとの認証情報の分離はありません
- このプロバイダーはセルフホストまたは信頼できるプライベート環境を想定しています
- チャット、ツール呼び出し、ストリーミング、構造化出力、圧縮、埋め込み、プリセット生成に対応`,
        vertex_footer: `このプロバイダーを設定したら、{configModel}でデフォルトモデルを変更できます`,
      },

      // /help elevenlabs
      elevenlabs: {
        description: `ElevenLabs音声合成の設定方法を学ぶ`,
        title: `ElevenLabs TTSの設定`,
        what_is_title: `ElevenLabsとは？`,
        what_is_description: `ElevenLabsはリアルなAI音声で話しかけるオプションの音声合成（TTS）プロバイダーです。
- 多くのボイスオプションを持つ高品質な音声合成
- メインAIプロバイダーと並行して動作
- 月間文字数制限のある無料ティア利用可能
- [ElevenLabs価格](https://elevenlabs.io/pricing)`,
        getting_key_title: `APIキーの取得：`,
        getting_key_description: `1. [ElevenLabs](https://elevenlabs.io/app/settings/api-keys)にアクセス
2. アカウントにサインインまたは新規登録
3. 新しいAPIキーを作成
4. {optionalkeyElevenlabsSet}を使用してAPIキーを入力`,
        choosing_voice_title: `ボイスの選択：`,
        choosing_voice_description: `APIキーを設定したら、使用するボイスを選択できます。
- {configVoiceElevenlabs}を使用して利用可能なボイスを参照・選択
- ボイスには異なる性別、年齢、アクセントが含まれます
- ボイス選択はいつでも変更・削除可能`,
        free_voices_title: `プリメイド音声（無料プラン対応）：`,
        free_voices_description: `プリメイド音声は無料プランでも利用できます。一覧は [ElevenLabs Premade Voices](https://elevenlabs-sdk.mintlify.app/voices/premade-voices) で確認し、{configVoiceElevenlabs} で各ペルソナに割り当てましょう。`,
        important_notes_title: `重要な注意点：`,
        important_notes_description: `- ElevenLabsはオプションです - 音声なしでもテキストで返信できます
- 音声メッセージを生成する際に文字数がカウントされます
- 無料ティアには月間制限があります - ElevenLabsダッシュボードで使用量を確認してください
- APIキーは{optionalkeyElevenlabsRemove}でいつでも削除できます`,
        footer: `APIキーは{optionalkeyElevenlabsRemove}でいつでも削除できます`,
      },

      // /help memory
      memory: {
        description: `TomoriBotの記憶システムについて学ぶ`,
        title: `記憶の仕組み`,
        embed_description: `会話を跨いでユーザーやサーバーに関する事実や情報を記憶する永続的な記憶システムがあります！これは**私が知っていること**（事実、コンテキスト、情報）についてです。**私がどう振る舞うか**（パーソナリティ、トーン、設定）については、代わりに{helpCustomization}をご覧ください！`,
        teaching_title: `物事を教える`,
        teaching_description: `{teach}を使用して**事実と情報**を記憶させます：
- **個人的な記憶**（{teachMemoryPersonal}）：個々のユーザーに関する事実
  - 例：「Alexは猫が好き」、「ダークモードを好む」、「ピーナッツアレルギー」
- **サーバーの記憶**（{teachMemoryServer}）：サーバー全体に関連する情報
  - 例：「ゲームナイトは毎週金曜日午後8時」、「NSFWの投稿禁止」、「お知らせには#generalを使用」`,
        forgetting_title: `忘れること`,
        forgetting_description: `{forget}を使用して記憶を削除：
- {forgetMemoryPersonal} - ユーザーに関する個人的な事実を削除
- {forgetMemoryServer} - サーバー全体の情報を削除`,
        how_it_works_title: `仕組み：`,
        how_it_works_description: `- **個人的な記憶**は全サーバーであなた専用に紐付けられ、あなたが積極的に参加している会話で返信する際にのみ記憶します
- **サーバーの記憶**はサーバー内にのみ留まり、サーバー内の会話で返信する際に常に記憶します
- 記憶は\`/forget\`コマンドを使用するまで保持されます`,
        tips_title: `記憶のヒント：`,
        tips_description: `- 好み、ニックネーム、重要な事実を教えてください
- サーバーの記憶には共有情報、内輪ネタ、サーバー文化を使用
- {dataExport}または{status}で定期的に記憶を確認
- 最良の結果を得るために記憶を簡潔明瞭に保つ

**プライバシー:** データ処理の詳細は\`/legal privacy\`をご覧ください`,
        documents_title: `ドキュメント知識庫`,
        documents_description: `サーバー管理者は参照用のドキュメントをアップロードできます：
- \`/teach document\`でテキスト、PDF、Markdownファイルをアップロード
- ドキュメントは検索可能な埋め込みとして分割して保存されます
- 会話に基づいて私は自動的に関連する内容を取得します
- \`/forget document\`でアップロードしたドキュメントを削除
- \`/config model embedding\`で埋め込みモデルの設定が必要`,
        shortterm_title: `短期記憶`,
        shortterm_description: `永続的な記憶に加え、最近の会話はSTM（短期記憶）として保持しています：
- 最近のメッセージはチャンネルごとにキャッシュされ、各ペルソナは同じサーバー内の他チャンネルにも最新のSTMを持ち越します
- 古い会話を自動的に要約し、文脈を効率的に保つことができます
- **クロスサーバー共有**はオプトイン制です：{personalStm}の\`crossserver\`オプションを使うと、あなた自身の他サーバーでの会話も参照できるようになります
- {personalStmClear}でユーザー固有のSTMをすべて削除できます
- STMは時間とともに自動的に期限切れになります`,
      },

      // /help customization
      customization: {
        description: `TomoriBotのパーソナリティと動作をカスタマイズする方法を学ぶ`,
        // Embed 1: Overview + Personas
        embed1_title: `TomoriBotのカスタマイズ`,
        embed1_description: `TomoriBotは高度にカスタマイズ可能です！私を本当にあなたのものにするために設定できるすべてがここにあります。これは**私がどう振る舞うか**（パーソナリティ、トーン、設定）についてです。**私が記憶していること**（事実、記憶）については、代わりに{helpMemory}をご覧ください！`,
        embed1_personas_title: `パーソナリティペルソナ`,
        embed1_personas_description: `私の核となるパーソナリティと動作を制御：

**ペルソナコマンド：**
- {personaCreate} - ゼロからカスタムパーソナリティを作成
- {personaGenerate} - 説明と画像に基づいてAIがパーソナリティを生成（構造化出力に対応したプロバイダーが必要。TomoriプリセットやSillyTavernカードをアップロードして既存キャラクターを変換することも可能）
- {personaDefault} - デフォルトのパーソナリティに切り替え
- {personaExport} - ペルソナを共有またはバックアップ用にエクスポート
- {personaImport} - ファイルからペルソナをインポート（独自のトリガーとウェブフックアバターを持つアルターペルソナとしてインポートも対応）
- {personaRemove} - アルターペルソナを削除
- {teach} - 話し方や行動を教える
- {serverAvatar} - プロフィール画像を変更`,
        embed1_what_personas_include_title: `ペルソナに含まれるもの：`,
        embed1_what_personas_include_description: `- パーソナリティ属性（特性、特徴、癖）
- サンプル対話（話し方を教える会話例）
- そのパーソナリティ用のカスタムサーバーアバター
- 動作とトーンの設定
- アルターペルソナ：独自のトリガー、ウェブフックアバター、パーソナリティを持つ別キャラクター`,
        embed1_footer: `次：教えるコマンド`,
        // Embed 2: Teaching System
        embed2_title: `教えるコマンド `,
        embed2_description: `## 教えるコマンド（\`/teach\`）
パーソナリティと知識を微調整：

**パーソナリティの形成：**
- {teachAttribute} - パーソナリティの特性を追加（例：「フレンドリー」、「皮肉っぽい」、「フォーマル」）
- {teachSampledialogue} - 話し方を形作る会話例を追加
- {configRename} - 自分を何と呼ぶべきかを設定

**サンプル対話の書き方：**
例で\`{user}\`と\`{bot}\`のプレースホルダーを使用：
- \`{user}\` = 実際のユーザーの名前/ニックネームに置き換えられます
- \`{bot}\` = 私の現在の名前に置き換えられます

**例：**
\`\`\`
ユーザーメッセージ：{user}：やあ、元気？
ボットの応答：{bot}：よぉ{user}！超元気だぜ、わかるだろ？
\`\`\`

**優れたサンプル対話のヒント：**
- 自然で会話的なやり取りを書く
- 表現したいパーソナリティの特性を含める
- 望むトーンを示す
- より良く学習できるように多様性を追加
- \`/persona export\`で共有する際にみんなに使えるようプレースホルダーを使用`,
        embed2_footer: `次：設定`,
        // Embed 3: Configuration & Management
        embed3_title: `設定＆管理`,
        embed3_description: `## 忘れるコマンド（\`/forget\`）
パーソナリティのカスタマイズを削除：

- {forgetAttribute} - 特定のパーソナリティ属性を削除
- {forgetSampledialogue} - サンプル対話の例を削除

---

## サーバー設定（\`/server\`）
サーバー全体の設定と動作：

**学習＆プライバシー：**
- {serverMemberpermissions} - 誰が私に物事を教えられるかを制御
- {serverBlacklist} - 特定のユーザーから学習したり記憶を使用するのを防ぐ

**自動トリガー動作：**
- {serverAutotriggerChannels} - メンションなしで応答するチャンネルを設定
- {serverAutotriggerThreshold} - 自動応答のメッセージ閾値を設定

**トリガー＆外観：**
- {serverTriggerAdd} - 反応するカスタムトリガーワードを追加（アルターペルソナにも対応しています）
- {serverTriggerDelete} - トリガーワードを削除
- {serverAvatar} - このサーバー用のカスタムプロフィール画像を設定

**チャンネルホワイトリスト＆クールダウン：**
- {configCooldown} - 私の応答間のグローバルクールダウンを設定
- {serverWhitelistChannel} - チャンネルをホワイトリストに追加（ホワイトリストされたチャンネルのみが私をトリガーできます）
- {serverWhitelistRole} - ロールホワイトリストにロールを追加/削除
- {serverWhitelistRemove} - チャンネルをホワイトリストから削除
- ホワイトリストされたチャンネルは、チャンネル固有の上書きを設定しない限りグローバルクールダウンを継承します

**ドキュメント：**
- {teachDocument} - 参照用のドキュメントをアップロード
- {forgetDocument} - アップロードされたドキュメントを削除`,
        embed3_footer: `次：ボット設定`,
        // Embed 4: Advanced Settings
        embed4_title: `詳細設定`,
        embed4_description: `## ボット設定（\`/config\`）
個人的なボット設定：

**AI設定：**
- {configModel} - 使用するAIモデルを選択
- {configTemperature} - 創造性/ランダム性を調整。高いほど応答がより多様に（1.0-2.0）
- {configHumanizer} - 応答の人間らしさを変更

**画像生成：**
- {generateImage} - プロンプトから画像を生成し、参照画像を編集する
- {configModelImage} - 画像生成モデルを選択（Text2ImageとImage2Image対応）

**システムプロンプト：**
- {configPromptChange} - カスタムシステム指示を追加（最大16000文字）
- {configPromptPreset} - プリセットシステムプロンプトを選択
- {configPromptClear} - デフォルトシステムプロンプトにリセット

**APIキー：**
- {configApikeySet} - AIプロバイダーのAPIキーを設定
- {configApikeyDelete} - APIキーを削除
- {configApikeyRotation} - 自動フェイルオーバーとロード分散用のバックアップAPIキーを管理
- {configBraveapiSet} - Brave Search APIキーを設定（オプション）
- {configBraveapiDelete} - Brave Search APIキーを削除

**パーソナライゼーション：**
- {configRename} - 自分を何と呼ぶかを変更
- {configTimezone} - 時間認識応答とリマインダー用のタイムゾーンを設定
- {configPermissions} - 機能のオン/オフを切り替え（画像生成を含む）
- {configUncensors} - 検閲なし出力オプションを設定
- {personalPrivacy} - 私への視認性を制御（完全に見えなくなるオプション利用可能）
- {serverInitializeExpressions} - サーバーの絵文字とステッカーの見た目を登録し、適切な場面で使えるようにする

**ドキュメント知識庫：**
- {configModelEmbedding} - ドキュメントアップロードとRAG用の埋め込みモデルを設定`,
        embed4_footer: `次：プロのヒント`,
        // Embed 5: Pro Tips
        embed5_title: `プロのヒント`,
        embed5_description: `- ペルソナ（デフォルトまたは生成）を基盤として始める
- 素早くパーソナリティを調整するには\`/teach attribute\`を使用
- サンプル対話では、属性や特性も示す例を使用すると効果的：
\`\`\`
ユーザーメッセージ：{user}：お気に入りの趣味は？
ボットの応答：{bot}：ふふ〜小さなぬいぐるみに小さな服を編むのが好きです〜♥
\`\`\`
- チャットして変更をテストし、しっくりくるまで繰り返す
- ペルソナをエクスポートしてバックアップするか、他のサーバーと共有！`,
      },

      // /help updates
      updates: {
        description: `TomoriBotの最新リリース情報を表示`,
        title: `TomoriBot {version} リリース！`,
        no_notes: `このバージョンのリリースノートはありません。`,
        footer: `更新情報が古い可能性があります。最新のリリースと更新は \`/support discord\` を確認してください。`,
        fetch_error_title: `最新リリース情報の取得に失敗`,
        fetch_error_description: `GitHubから最新リリース情報を取得できませんでした。しばらくお待ちください。または、[GitHubリリース](https://github.com/Bredrumb/TomoriBot/releases)ページを直接確認してください。`,
      },

      // /help mcp
      mcp: {
        description: `MCPツールサーバーの追加と管理方法を学ぶ`,
        title: `MCPサーバーセットアップガイド`,
        description_text: `MCP（Model Context Protocol）サーバーは、外部ツールでTomoriの機能を拡張します。始め方を説明します。`,
        online_title: `オンラインMCPの追加`,
        online_description: `HTTPSエンドポイントを持つ公開MCPサーバーであれば、どれでも追加できます。Smithery.aiはその一例に過ぎません。\n\n**Smithery.aiを使う場合：**\n**1.** [smithery.ai](https://smithery.ai) にアクセスし、アカウントを作成してプロフィールからAPIキーを生成します。\n**2.** カタログを閲覧し、追加したいMCPを開きます。ページに表示されている**接続URL**をコピーします（例：\`https://youtube.run.tools\`）。\n**3.** {configMcpAdd} を実行し、**URL**フィールドに接続URLを、**認証トークン**フィールドにSmithery APIキーを貼り付けます。\n\n**他のソースを使う場合：**\n認証が不要なMCPサーバーの場合は、**認証トークン**フィールドを空白のままにしてください。サーバーによっては別の認証形式を使用する場合があります。詳細はそのサーバーのドキュメントを確認してください。\n\n認証トークンは保存後に暗号化され、平文で表示されることはありません。`,
        local_title: `ローカルMCPの追加（自己ホスト限定）`,
        local_description: `ローカルMCPサーバーは、**自己ホストのTomoriBotインスタンスでのみ対応しています**。公式ホスト版のbotはセキュリティのためHTTPSが必要で、ローカル/プライベートアドレスはブロックされます。\n\n自己ホストの場合は、ローカルサーバーのURLを指定してください（例：\`http://localhost:3000/sse\`）。ローカルサーバーには認証トークンは不要です。`,
        removing_title: `MCPサーバーの削除`,
        removing_description: `{configMcpRemove} を使えば、いつでもサーバーの登録を解除できます。削除すると即座に接続が切断され、新しいサーバーのスロットが解放されます。`,
        security_title: `セキュリティに関する警告`,
        security_description: `**信頼できるMCPサーバーのみ追加してください。**\n\n悪意のあるMCPサーバーは以下のことが可能です：\n- **プロンプトインジェクション** — Tomoriへ隠し指示を送り、動作を操作する\n- **データ漏洩** — ツールに渡されたデータ（メッセージやファイル内容など）を外部へ送信する\n- **有害または虚偽の結果** を返し、Tomoriがそれをサーバーに中継する\n\nMCPサーバーはブラウザ拡張機能やサードパーティアプリと同様の注意を持って扱ってください。不安な場合は追加しないでください。`,
        footer: `Smithery.aiはサードパーティのサービスであり、TomoriBotとは無関係です。追加前に必ずMCPの提供ツールを確認してください。`,
      },
    },

    // 法的文書コマンド
    legal: {
      privacy: {
        description: `TomoriBotのプライバシーポリシーを表示`,
        title: `プライバシーポリシー`,
        description_text: `TomoriBotのプライバシーポリシーを表示して、データの取り扱いについて理解してください。これは公式ホスト版インスタンスに適用されます。セルフホスト版インスタンスは独自のデータ処理を制御します。`,
        link_title: `完全なプライバシーポリシー`,
      },
      terms: {
        description: `TomoriBotの利用規約を表示`,
        title: `利用規約`,
        description_text: `TomoriBotの利用規約を表示して、ボットの使用に関するルールとガイドラインを理解してください。これは公式ホスト版インスタンスに適用されます。セルフホスト版インスタンスはAGPLv3ライセンスに準拠します。`,
        link_title: `完全な利用規約`,
      },
      license: {
        description: `TomoriBotのオープンソースライセンスを表示`,
        title: `オープンソースライセンス`,
        description_text: `TomoriBotはGNU Affero General Public License v3.0（AGPLv3）の下でライセンスされたオープンソースソフトウェアです。このライセンスにより、コードを自由に使用、変更、配布できますが、公開ホストされたインスタンスへの変更もオープンソース化する必要があります。`,
        link_title: `完全なAGPLv3ライセンス`,
      },
    },

    // NovelAI画像生成コマンド
    novelai: {
      charreference: {
        description: `自分またはペルソナ用のNovelAIキャラクター参照画像を保存またはクリアします。`,
        target_description: `自分のプロフィールかサーバーのペルソナかを選択します。`,
        target_choice_me: `自分`,
        target_choice_persona: `ペルソナ`,
        image_description: `保存する参照画像。空欄で現在の画像をクリアします。`,
        persona_select_title: `ペルソナを選択`,
        invalid_image_title: `無効な画像`,
        invalid_image_description: `キャラクター参照画像には画像添付ファイルを指定してください。`,
        download_failed_title: `ダウンロードに失敗しました`,
        download_failed_description: `選択した画像添付のダウンロードに失敗しました。もう一度お試しください。`,
        conversion_failed_title: `画像変換に失敗しました`,
        conversion_failed_description: `保存用にその画像をPNGへ変換できませんでした。別の画像をお試しください。`,
        success_title: `キャラクター参照画像を更新しました`,
        success_me_description: `あなたのNovelAIキャラクター参照画像を更新しました。`,
        success_persona_description: `**{persona_name}**のNovelAIキャラクター参照画像を更新しました。`,
        cleared_title: `キャラクター参照画像をクリアしました`,
        cleared_me_description: `あなたのNovelAIキャラクター参照画像をクリアしました。`,
        cleared_persona_description: `**{persona_name}**のNovelAIキャラクター参照画像をクリアしました。`,
      },
      tags: {
        description: `サーバー・ペルソナ・ユーザープロフィール用のNovelAIタグ設定を管理します。`,
        style: {
          description: `このサーバー全体で使うNovelAIスタイルタグを設定します。`,
          modal_title: `スタイルタグ`,
          tags_input_label: `スタイルタグ`,
          tags_input_description: `このサーバーのすべてのNovelAI画像プロンプトの先頭に付くカンマ区切りタグです。空欄で全スタイルタグをクリアします。`,
          tags_input_placeholder: `8k, absurdres, watercolor, soft lighting`,
          no_tags_title: `タグが未入力です`,
          no_tags_description: `少なくとも1つのスタイルタグを入力してください。`,
          too_many_tags_title: `タグが多すぎます`,
          too_many_tags_description: `このサーバーには最大{max_tags}個までスタイルタグを設定できます。`,
          tag_too_long_title: `タグが長すぎます`,
          tag_too_long_description: `各スタイルタグは{max_length}文字以下にしてください。`,
          success_title: `スタイルタグを更新しました`,
          success_description: `サーバー全体のスタイルタグを更新しました：\n\`\`\`\n{tag_list}\n\`\`\``,
          cleared_title: `スタイルタグを初期値に戻しました`,
          cleared_description: `サーバー全体のスタイルタグを初期値に戻しました：\n\`\`\`\n{tag_list}\n\`\`\``,
        },
        negative: {
          description: `このサーバー全体で使うNovelAIネガティブタグを設定します。`,
          modal_title: `ネガティブタグ`,
          tags_input_label: `ネガティブタグ`,
          tags_input_description: `このサーバーのNovelAI画像生成に使うカンマ区切りのネガティブタグです。空欄でサーバー上書きをクリアし、フォールバックのネガティブプロンプトに戻します。`,
          tags_input_placeholder: `lowres, blurry, bad anatomy, watermark`,
          no_tags_title: `タグが未入力です`,
          no_tags_description: `少なくとも1つのネガティブタグを入力してください。`,
          too_many_tags_title: `タグが多すぎます`,
          too_many_tags_description: `このサーバーには最大{max_tags}個までネガティブタグを設定できます。`,
          tag_too_long_title: `タグが長すぎます`,
          tag_too_long_description: `各ネガティブタグは{max_length}文字以下にしてください。`,
          success_title: `ネガティブタグを更新しました`,
          success_description: `サーバー全体のネガティブタグを更新しました：\n\`\`\`\n{tag_list}\n\`\`\``,
          cleared_title: `ネガティブタグを初期値に戻しました`,
          cleared_description: `サーバー全体のネガティブタグを初期値に戻しました：\n\`\`\`\n{tag_list}\n\`\`\``,
        },
        me: {
          description: `自分用のNovelAIキャラクタータグを設定します。`,
          modal_title: `自分のキャラクタータグ`,
          tags_input_label: `キャラクタータグ`,
          tags_input_description: `あなたのNovelAIプロフィール用のカンマ区切り画像ボードスタイルタグです。空欄でクリアします。`,
          tags_input_placeholder: `1girl, short hair, red eyes, school uniform`,
          no_tags_title: `タグが未入力です`,
          no_tags_description: `少なくとも1つのキャラクタータグを入力してください。`,
          too_many_tags_title: `タグが多すぎます`,
          too_many_tags_description: `個人キャラクタータグは最大{max_tags}個まで設定できます。`,
          tag_too_long_title: `タグが長すぎます`,
          tag_too_long_description: `各キャラクタータグは{max_length}文字以下にしてください。`,
          success_title: `キャラクタータグを更新しました`,
          success_description: `あなたのNovelAIキャラクタータグを更新しました：\n\`\`\`\n{tag_list}\n\`\`\``,
          cleared_title: `キャラクタータグをクリアしました`,
          cleared_description: `あなたのNovelAIキャラクタータグをすべてクリアしました。`,
        },
        character: {
          description: `ペルソナプロフィール用のNovelAIキャラクタータグを設定します。`,
          modal_title: `キャラクタータグ`,
          persona_select_label: `ペルソナ`,
          persona_select_description: `キャラクタータグを設定するペルソナを選択してください。`,
          persona_select_placeholder: `ペルソナを選択...`,
          tags_input_label: `キャラクタータグ`,
          tags_input_description: `カンマ区切りの画像ボードスタイルのタグ（例：1girl, short hair, red eyes）。大文字小文字を区別します。`,
          tags_input_placeholder: `1girl, short hair, red eyes, school uniform`,
          no_tags_title: `タグが未入力です`,
          no_tags_description: `少なくとも1つのキャラクタータグを入力してください。`,
          too_many_tags_title: `タグが多すぎます`,
          too_many_tags_description: `1ペルソナあたり最大{max_tags}タグまで設定できます。`,
          tag_too_long_title: `タグが長すぎます`,
          tag_too_long_description: `各タグは{max_length}文字以下にしてください。`,
          success_title: `キャラクタータグを更新しました`,
          success_description: `**{persona_name}**のキャラクタータグを更新しました：\n\`\`\`\n{tag_list}\n\`\`\``,
          cleared_title: `キャラクタータグをクリアしました`,
          cleared_description: `**{persona_name}**のキャラクタータグをすべてクリアしました。`,
        },
      },
      preset: {
        text: {
          description: `このサーバーのテキスト生成設定にNovelAIサンプリングプリセットを適用します。`,
          not_novelai_title: `NovelAIプロバイダーが必要です`,
          not_novelai_description: `このコマンドはAIプロバイダーがNovelAIに設定されている場合にのみ使用できます。\`/config apikey set\` でプロバイダーを切り替えてください。`,
          not_kayra_erato_title: `KayraまたはEratoが必要です`,
          not_kayra_erato_description: `サンプリングプリセットは **kayra-v1** および **llama-3-erato-v1** モデルのみで利用可能です。\`/config model text\` でモデルを切り替えてください。`,
          modal_title: `サンプリングプリセットを選択`,
          select_label: `サンプリングプリセット`,
          select_description: `テキスト生成に適用するプリセットを選択してください。`,
          select_placeholder: `サンプリングプリセットを選択...`,
          success_title: `プリセットを適用しました`,
          success_description: `サンプリングプリセット **{preset_name}** を適用しました。温度、トップK、トップP、ミンPがサーバー設定に反映されました。`,
        },
      },
      image: {
        description: `このサーバーのNovelAI画像生成モデルとパラメータ上書きを管理します。`,
        generate: {
          description: `画像掲示板タグ形式のプロンプトと任意のキャラクター参照画像でNovelAI画像を生成します。`,
          modal_title: `NovelAI画像生成`,
          prompt_label: `プロンプトタグ`,
          prompt_modal_description: `メインシーン用の画像掲示板タグです。`,
          prompt_placeholder: `例: 1girl, solo, cafe, window light, detailed eyes`,
          prompt_description: `シーン用の画像掲示板タグ（例: 1girl, solo, cafe, window light, detailed eyes）。`,
          negative_tags_label: `追加ネガティブタグ`,
          negative_tags_modal_description: `今回の生成だけに追加する任意のネガティブタグです。`,
          negative_tags_placeholder: `例: blurry, text, watermark, extra fingers`,
          orientation_description: `portrait・landscape・square のいずれかを選択します。`,
          orientation_label: `向き`,
          orientation_modal_description: `画像の向きを選択します。`,
          orientation_choice_portrait: `Portrait`,
          orientation_choice_landscape: `Landscape`,
          orientation_choice_square: `Square`,
          negative_tags_description: `今回の生成にだけ追加する任意のネガティブタグです。`,
          character_reference_label: `キャラクター参照画像`,
          character_reference_modal_description: `単一キャラクター用の任意の参照画像です。`,
          character_reference_description: `V4モデルで単一キャラクターの見た目を誘導する任意の参照画像です。`,
          success_title: `NovelAI画像を生成しました`,
          success_notice_title: `画像を投稿しました`,
          success_notice_description: `NovelAI画像を生成し、チャンネルに投稿しました。`,
          field_prompt: `プロンプトタグ`,
          field_model: `モデル`,
          field_generation_time: `生成時間`,
          field_orientation: `向き`,
          field_negative_tags: `追加ネガティブタグ`,
          no_api_key_title: `NovelAI APIキーが必要です`,
          no_api_key_description: `このサーバーでは利用可能なNovelAI APIキーがありません。\`/optionalkey novelai set\` で設定するか、メインプロバイダーをNovelAIに切り替えてください。`,
          invalid_reference_title: `無効なキャラクター参照画像です`,
          invalid_reference_description: `キャラクター参照画像には、NovelAIが読み取れる有効な画像添付を指定してください。`,
          character_reference_requires_v4_title: `V4モデルが必要です`,
          character_reference_requires_v4_description: `キャラクター参照画像は現在NovelAI V4モデルでのみ利用できます。現在の有効モデル: **{model}**。`,
          auth_error_title: `NovelAI認証に失敗しました`,
          auth_error_description: `NovelAIが画像生成リクエストを拒否しました。APIキーとサブスクリプション状態を確認してから再試行してください。`,
          quota_error_title: `NovelAI生成クォータを使い切りました`,
          quota_error_description: `このアカウントではNovelAI画像生成に必要なクォータまたはAnlasクレジットが不足しています。アカウントを補充するか、クォータのリフレッシュ後に再試行してください。`,
          rate_limit_error_title: `NovelAIのレート制限に達しました`,
          rate_limit_error_description: `NovelAIのレート制限により画像生成できませんでした。少し待ってから再試行してください。`,
          error_title: `NovelAI画像生成に失敗しました`,
          error_description: `NovelAIで画像を生成できませんでした。\n\`\`\`\n{error}\n\`\`\``,
        },
        model: {
          description: `このサーバーでNovelAI画像ツールが使う拡散モデルを選択します。`,
          modal_title: `NovelAI画像生成モデル`,
          select_label: `画像モデル`,
          select_description: `専用のNovelAIモデルを選ぶか、Automaticで共有/既定動作を使います。`,
          select_placeholder_current_override: `現在の上書き値: {model}`,
          select_placeholder_current_automatic: `Automaticモード: 現在は {model}`,
          automatic_label: `Automatic`,
          automatic_description: `共有画像モデルがNovelAIならそれを使い、そうでなければNovelAI既定モデルを使います。`,
          no_models_title: `利用可能なNovelAIモデルがありません`,
          no_models_description: `このBot環境ではNovelAI画像モデルが利用できません。`,
          invalid_model_title: `無効なモデルです`,
          invalid_model_description: `有効なNovelAI画像モデルを選択してください。`,
          already_selected_title: `モデルは既に選択済みです`,
          already_selected_description: `NovelAI画像モデルモードは既に **{mode}** です。`,
          success_title: `NovelAI画像モデルを更新しました`,
          success_description: `このサーバーのNovelAI画像モデル挙動:\n\`\`\`\nMode: {mode}\nEffective model: {effective_model}\nSource: {source}\n\`\`\``,
          source_override: `NovelAIモデル上書き`,
          source_shared: `共有画像モデル (/config model image)`,
          source_default: `NovelAI既定モデル`,
        },
        params: {
          description: `このサーバー用にNovelAI画像生成のサンプラーと品質設定を上書きします。`,
          modal_title: `NovelAI画像生成パラメータ`,
          sampler_label: `Sampler`,
          sampler_description: `変更したいSamplerを選択してください。未選択のままなら現在の値を維持します。`,
          sampler_placeholder_current: `現在の上書き値: {sampler}`,
          sampler_placeholder_default: `現在、上書きなし`,
          sampler_option_env_default_label: `Use Default`,
          sampler_option_env_default_desc: `Samplerのサーバー上書きを解除します。`,
          option_default_suffix: `（デフォルト）`,
          sampler_option_k_euler_ancestral: `Euler Ancestral`,
          sampler_option_k_euler: `Euler`,
          sampler_option_k_dpmpp_2s_ancestral: `DPM++ 2S Ancestral`,
          sampler_option_k_dpmpp_2m_sde: `DPM++ 2M SDE`,
          sampler_option_k_dpmpp_2m: `DPM++ 2M`,
          sampler_option_k_dpmpp_sde: `DPM++ SDE`,
          steps_label: `Steps`,
          steps_description: `1〜50の整数。空欄でデフォルトを使います。`,
          steps_placeholder: `例: 23`,
          scale_label: `Prompt Guidance`,
          scale_description: `0.0〜10.0の小数。空欄でデフォルトを使います。`,
          scale_placeholder: `例: 5`,
          noise_schedule_label: `Noise Schedule`,
          noise_schedule_description: `変更したいNoise Scheduleを選択してください。未選択のままなら現在の値を維持します。`,
          noise_schedule_placeholder_current: `現在の上書き値: {noise_schedule}`,
          noise_schedule_placeholder_default: `現在、上書きなし`,
          noise_schedule_option_default_label: `Use Default`,
          noise_schedule_option_default_desc: `Noise Scheduleのサーバー上書きを解除します。`,
          noise_schedule_option_karras: `Karras`,
          noise_schedule_option_exponential: `Exponential`,
          noise_schedule_option_polyexponential: `Polyexponential`,
          cfg_rescale_label: `Prompt Guidance Rescale`,
          cfg_rescale_description: `0.0〜1.0の小数。空欄でデフォルトを使います。`,
          cfg_rescale_placeholder: `例: 0.0`,
          invalid_sampler_title: `無効なSamplerです`,
          invalid_sampler_description: `Samplerは次のいずれかである必要があります: {options}。`,
          invalid_steps_title: `無効なStepsです`,
          invalid_steps_description: `Stepsは{min}〜{max}の整数で入力してください。`,
          invalid_scale_title: `無効なPrompt Guidanceです`,
          invalid_scale_description: `Prompt Guidanceは{min}〜{max}の数値で入力してください。`,
          invalid_noise_schedule_title: `無効なNoise Scheduleです`,
          invalid_noise_schedule_description: `Noise scheduleは次のいずれかである必要があります: {options}。`,
          invalid_cfg_rescale_title: `無効なPrompt Guidance Rescaleです`,
          invalid_cfg_rescale_description: `Prompt Guidance Rescaleは{min}〜{max}の数値で入力してください。`,
          success_title: `画像生成パラメータを更新しました`,
          success_description: `このサーバーの有効なNovelAI画像生成パラメータ:\n\`\`\`\nSampler: {sampler}\nSteps: {steps}\nPrompt Guidance: {scale}\nNoise schedule: {noise_schedule}\nPrompt Guidance Rescale: {cfg_rescale}\n\`\`\``,
        },
      },
      attg: {
        description: `NovelAI KayraおよびEratoプロンプト用のAuthor/Title/Tags/Genre/Starsメタデータを設定します。`,
        modal_title: `ATTGの設定`,
        persona_select_title: `ペルソナを選択`,
        persona_select_description: `ATTGメタデータを設定するペルソナを選択してください。`,
        author_label: `作者`,
        author_placeholder: `例: 山田太郎`,
        title_label: `タイトル`,
        title_placeholder: `例: 私の物語`,
        tags_label: `タグ`,
        tags_placeholder: `例: ロマンス, 冒険`,
        genre_label: `ジャンル`,
        genre_placeholder: `例: ファンタジー, 日常`,
        stars_label: `スター (Eratoのみ)`,
        stars_placeholder: `1-5`,
        stars_description: `Eratoモデルプロンプト用の品質評価 (1-5)。空欄でクリア。`,
        invalid_stars_title: `スター値が無効です`,
        invalid_stars_description: `スターは1〜5の整数か、空欄にしてください。`,
        success_title: `ATTGメタデータを更新しました`,
        success_description: `**{persona_name}**のATTGメタデータを更新しました。`,
        cleared_title: `ATTGメタデータをクリアしました`,
        cleared_description: `**{persona_name}**のATTGメタデータをすべてクリアしました。`,
      },
    },

    // ボットの手動制御コマンド
    bot: {
      generate: {
        description: `現在のチャンネルの流れに合わせて素早く実行する手動生成コマンド。`,
        image: {
          description: `このチャンネルの直近コンテキストから素早くシーン画像を生成します。`,
          missing_permissions_title: `権限がありません`,
          missing_permissions_description: `このチャンネルでシーン画像を生成するには、チャンネルの閲覧、メッセージ履歴の読み取り、メッセージ送信、ファイル添付の権限が必要です。`,
          cooldown_active: `このサーバーの管理者がクールダウンを設定しています。\`/bot generate image\` を再度使用するまで、あと **{seconds}** 秒お待ちください。このクールダウンはメッセージトリガーや他の手動 /bot 操作と共有されています。`,
          channel_not_whitelisted: `このサーバーではホワイトリスト制限が有効です。\`/bot generate image\` はホワイトリスト登録チャンネル内で、かつホワイトリスト登録ロールを持つメンバーのみ使用できます。`,
          no_messages_title: `シーン用コンテキストが見つかりません`,
          no_messages_description: `シーン画像を組み立てるのに十分な最近のチャンネル文脈が見つかりませんでした。少し会話してから、もう一度 \`/bot generate image\` を試してください。`,
          no_backend_title: `使える画像バックエンドがありません`,
          no_backend_description: `このサーバーで今使える画像バックエンドが見つかりませんでした。**{current_provider}** に有効な画像モデルを設定するか、NovelAI で描画したい場合は NovelAI のオプション API キーを追加してください。`,
          planner_unavailable_title: `計画用モデルがありません`,
          planner_unavailable_description: `現在のプロバイダーで構造化出力に対応したモデルが見つからないため、今はシーン画像を計画できません。`,
          planner_failed_title: `シーン計画に失敗しました`,
          planner_failed_description: `最近のチャンネル文脈を画像プランに変換できませんでした: {error}`,
          success_title: `シーン画像を投稿しました`,
          success_description: `最近のチャンネル文脈から構図を計画し、このチャンネルに画像を投稿しました。`,
          modal: {
            title: `シーン画像`,
            prompt_label: `追加指示（任意）`,
            prompt_description: `シーンプランナーに反映してほしい補足、雰囲気、修正を入力してください`,
            prompt_placeholder: `例: 雨を強調して、やわらかめの雰囲気で、二人とも見えるように`,
            setting_label: `構図プリセット`,
            setting_description: `この fire-and-forget シーン画像に使う構図プリセットを選択してください`,
            setting_storybeat_label: `ストーリービート`,
            setting_storybeat_description: `直近の場面を広めに切り取るシネマ風構図`,
            setting_character_label: `キャラクター重視`,
            setting_character_description: `主役や話者に寄せた近めの構図`,
            setting_snapshot_label: `スクエアスナップ`,
            setting_snapshot_description: `今この瞬間を収めるバランス型の正方形構図`,
            setting_vertical_label: `スマホ壁紙`,
            setting_vertical_description: `シルエットを活かした縦長構図`,
            backend_label: `画像バックエンド`,
            backend_description: `どのレンダラーでこのシーン画像を生成するか選択してください`,
            backend_current_label: `現在のプロバイダー`,
            backend_current_description: `{provider} の通常の画像生成フローとプロンプト形式を使います`,
            backend_novelai_label: `NovelAI`,
            backend_novelai_description: `シーンを NovelAI 向けタグに変換し、NovelAI の画像ツールで生成します`,
            persona_label: `送信ペルソナ`,
            persona_description: `生成された画像を投稿するペルソナを選んでください`,
          },
        },
      },
      respond: {
        description: `このチャンネルの最新メッセージに手動で応答をトリガーします。`,
        prompt_description: `コンテキスト末尾に追加する任意のシステムプロンプト。`,
        prompt_label: `プロンプト（任意）`,
        prompt_placeholder: `システム指示を追加（任意）...`,
        prefill_description: `私に続きを書いてほしい、アシスタントの返答の書き出し（任意）。`,
        prefill_label: `プリフィル（任意）`,
        prefill_placeholder: `アシスタントのプリフィルを追加（任意）...`,
        success_title: `手動応答がトリガーされました`,
        success_description: `このチャンネルの最新メッセージに応答しています...`,
        missing_permissions_title: `権限がありません`,
        missing_permissions_description: `このチャンネルのメッセージ履歴を読み取る権限がありません。**チャンネルを見る**および**メッセージ履歴を読む**権限があることを確認してください。`,
        select_persona_title: `ペルソナを選択`,
        select_persona_label: `ペルソナを選択`,
        select_persona_description: `応答するペルソナを選択してください。`,
        select_persona_placeholder: `応答するペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        embed_hide_notice: `\`/config permissions\` でこの埋め込みを非表示にできます。`,
        use_reasoning_label: `推論を使用`,
        use_reasoning_description: `利用可能な最も賢いモデルを使用して高度な推論モードを切り替えます。`,
        use_reasoning_placeholder: `推論モードを選択してください...`,
        use_reasoning_yes: `はい`,
        use_reasoning_yes_description: `最も賢い推論モデルを使用してより徹底した応答を生成します。`,
        use_reasoning_no: `いいえ`,
        use_reasoning_no_description: `通常の応答のために標準モデルを使用します。`,
        no_smart_model_title: `推論モデルが見つかりません`,
        no_smart_model_description: `現在のAIプロバイダーに推論モデルが見つかりませんでした。\`/config apikey set\`を使用して、推論モデルをサポートするプロバイダーに切り替えてください。`,
        no_messages_title: `メッセージが見つかりません`,
        no_messages_description: `このチャンネルにメッセージが見つかりません。 \`/bot respond\` を使う前に、少なくとも1件メッセージを送信してください。`,
        cooldown_active: `このサーバーの管理者がクールダウンを設定しています。\`/bot respond\` を再度使用するまで、あと **{seconds}** 秒お待ちください。このクールダウンはメッセージトリガーと共有されています。`,
        channel_not_whitelisted: `このサーバーではホワイトリスト制限が有効です。\`/bot respond\` はホワイトリスト登録チャンネル内で、かつホワイトリスト登録ロールを持つメンバーのみ使用できます。`,
      },
      kill: {
        description: `このチャンネルで現在のストリーム応答を停止し、キュー済み応答をすべてクリアします。`,
        success_title: `ストリームを停止しました`,
        success_description: `進行中の応答ストリーム（ある場合）を停止し、このチャンネルのキュー済み応答をクリアしました。`,
        nothing_to_stop_title: `停止・クリア対象がありません`,
        nothing_to_stop_description: `このチャンネルには停止できる進行中の応答ストリームも、クリアできるキュー済み応答もありません。`,
      },
      impersonate: {
        description: `ペルソナ、ユーザー、またはシステムプロンプトになりすます。`,
        target_description: `なりすます対象を選択してください。`,
        target_persona: `ペルソナ`,
        target_me: `自分`,
        target_user: `ユーザー`,
        target_system: `システム`,
        user_select_title: `ユーザーを選択`,
        user_select_description: `なりすますユーザーを選択してください。`,
        user_select_placeholder: `なりすますユーザーを選択...`,

        // ペルソナのなりすまし
        persona_modal_title: `ペルソナになりすます`,
        persona_select_label: `ペルソナを選択`,
        persona_select_placeholder: `なりすますペルソナを選択...`,
        persona_message_label: `メッセージ`,
        persona_message_placeholder: `ペルソナとして送信するメッセージを入力...`,
        persona_success_title: `メッセージを送信しました`,
        persona_success_description: `{persona}としてメッセージを送信しました。`,
        persona_impersonation_notice_description: `\`/config permissions\`で「なりすまし埋め込みを非表示」権限を有効にすると、この埋め込みを非表示にできます。`,
        persona_impersonation_notice_footer: `{user}によるなりすまし`,
        user_impersonation_notice_description: `\`/config permissions\`で「なりすまし埋め込みを非表示」権限を有効にすると、この埋め込みを非表示にできます。`,
        user_impersonation_notice_footer: `{user}が{target}のなりすましをトリガーしました`,

        // ユーザーのなりすまし
        me_success_title: `ユーザーなりすましが発動しました`,
        me_success_description: `{user}としてメッセージを生成できました.`,
        no_messages_title: `メッセージが見つかりません`,
        no_messages_description: `このチャンネルにメッセージが見つかりません。ユーザーなりすましを使用する前に、少なくとも1つのメッセージを送信してください。`,
        cooldown_active: `このサーバーの管理者がクールダウンを設定しています。\`/bot impersonate me\` を再度使用するまで、あと **{seconds}** 秒お待ちください。このクールダウンはメッセージトリガーと\`/bot respond\`と共有されています。`,
        cooldown_active_user: `このサーバーの管理者がクールダウンを設定しています。\`/bot impersonate user\` を再度使用するまで、あと **{seconds}** 秒お待ちください。このクールダウンはメッセージトリガーと\`/bot respond\`と共有されています。`,
        channel_not_whitelisted: `このサーバーではホワイトリスト制限が有効です。\`/bot impersonate me\` はホワイトリスト登録チャンネル内で、かつホワイトリスト登録ロールを持つメンバーのみ使用できます。`,
        channel_not_whitelisted_user: `このサーバーではホワイトリスト制限が有効です。\`/bot impersonate user\` はホワイトリスト登録チャンネル内で、かつホワイトリスト登録ロールを持つメンバーのみ使用できます。`,

        // システムのなりすまし
        system_modal_title: `システムプロンプト注入`,
        system_content_label: `システムプロンプト`,
        system_content_placeholder: `システム指示を入力...`,
        system_title: `システムメッセージ`, // これは検出をトリガーする埋め込みタイトルです
        system_injected_footer: `{user}により注入`,
        system_success_title: `システムプロンプトを注入しました`,
        system_success_description: `システムプロンプトが会話に注入されました。ボットは次のメッセージでこの指示を認識します。`,

        // エラー
        missing_permissions_title: `権限が不足しています`,
        missing_permissions_description: `このチャンネルでメッセージを送信するか、Webhookを管理する権限がありません。`,
        webhook_error_title: `Webhookエラー`,
        webhook_error_description: `なりすまし用のWebhookの作成に失敗しました。エラー：{error}`,
        no_personas_title: `ペルソナが見つかりません`,
        no_personas_description: `このサーバーにはペルソナが設定されていません。まず\`/config setup\`を使用してください。`,
      },
    },

    // ご褒美コマンド
    reward: {
      description: `私へのご褒美インタラクション。`,
      headpat: {
        description: `ヘッドパットして応答をトリガーします。`,
        embed_title: `🫳 ヘッドパット・タイム！`,
        embed_description: `{user}は現在{bot}をなでています。`,
      },
      hug: {
        description: `ハグして応答をトリガーします。`,
        embed_title: `🤗 ハグ・タイム！`,
        embed_description: `{user}は{bot}をぎゅっと抱きしめています。`,
      },
      kiss: {
        description: `キスして応答をトリガーします。`,
        embed_title: `💋 キス・タイム！`,
        embed_description: `{user}は{bot}にキスしました。`,
      },
      tickle: {
        description: `くすぐって応答をトリガーします。`,
        embed_title: `🤭 くすぐり・タイム！`,
        embed_description: `{user}は{bot}をくすぐっています。`,
      },
    },

    // サポートコマンド
    support: {
      discord: {
        description: `バグ報告、フィードバック、コミュニティチャットのための公式Discordサーバーリンクを取得します。`,
        title: `Discordサーバーに参加`,
        description_text: `TomoriBotのヘルプが必要ですか？またはコミュニティと交流したいですか？\n\n🔗 **Discordサーバー**: https://discord.gg/bjCfHm9QsB\n\n参加して:\n• バグや問題を報告\n• フィードバックや提案を共有\n• 他のユーザーや開発チームとチャット\n• 新機能の最新情報を入手`,
      },
    },

    // 貢献コマンド
    contribute: {
      github: {
        description: `GitHubリポジトリのリンクを取得し、TomoriBotへの貢献方法を学びます。`,
        title: `TomoriBotに貢献する`,
        description_text: `TomoriBotをより良くするお手伝いをしたいですか？貢献をお待ちしています！\n\n🔗 **GitHubリポジトリ**: https://github.com/Bredrumb/TomoriBot\n\n貢献方法:\n• GitHubでリポジトリにスターを付ける ⭐\n• バグ報告や機能リクエストを送信\n• コードの改善や新機能を貢献\n• TomoriBotを他の言語に翻訳するお手伝い\n• ドキュメントの改善`,
      },
    },

    // 寄付コマンド
    donate: {
      kofi: {
        description: `Ko-fiを通じてTomoriBotの開発を支援します。`,
        title: `TomoriBotの開発を支援`,
        description_text: `TomoriBotを使うのが好きですか？無料で維持し、継続的な開発を支援してください！\n\n🔗 **Ko-fi**: https://ko-fi.com/bredrumb\n\nあなたの寄付は以下に役立ちます:\n• TomoriBotの運営と保守\n• 新機能と改善の追加\n• サーバーコストと開発時間のサポート\n• TomoriBotを完全に無料で維持\n\n大小問わず、すべての貢献に心から感謝します！ ❤️`,
      },
    },

    // 設定コマンド（管理者のみ）
    config: {
      options: {
        add: `追加`,
        remove: `削除`,
        enable: `有効化`,
        disable: `無効化`,
      },
      // APIキー管理（サブコマンドグループ）
      apikey: {
        description: `AIプロバイダーのAPIキーを管理`,
        set: {
          description: `選択したAIプロバイダーのAPIキーを設定します。`,
          modal_title: `APIキーの設定`,
          provider_label: `AIプロバイダー`,
          provider_description: `APIキーに対応するAIプロバイダーを選択してください`,
          provider_placeholder: `プロバイダーを選択...`,
          api_key_label: `プロバイダーAPIキー`,
          api_key_description: `このキーは安全に保存されます。取得方法については、'/help apikey'コマンドを使用してください。ヒント：設定の保存には /config provider switch をお使いください。`,
          api_key_description_with_custom: `APIキー、またはCustomの場合はOpenAIエンドポイントURL（例：http://localhost:11434/v1）`,
          api_key_placeholder: `このキーは誰とも共有しないでください`,
          no_providers_title: `利用可能なプロバイダーがありません`,
          no_providers_description: `データベースに利用可能なAIプロバイダーがありません。ボットの管理者に連絡してください。`,
          invalid_key_title: `無効なAPIキー形式`,
          invalid_key_description: `提供されたAPIキーは短すぎるか無効のようです。有効なキーを提供してください。`,
          validating_key: `APIキーを検証中...`,
          unsupported_provider_title: `サポートされていないプロバイダー`,
          unsupported_provider_description: `プロバイダー「{provider}」は現在APIキーの検証をサポートしていません。`,
          validation_error_title: `検証エラー`,
          validation_error_description: `APIキーの検証中にエラーが発生しました。もう一度お試しください。`,
          key_validation_failed_title: `APIキーの検証に失敗しました`,
          key_validation_failed_description: `{provider}に対して提供されたAPIキーは無効です。キーを確認してもう一度お試しください。`,
          no_default_model_title: `デフォルトモデルが見つかりません`,
          no_default_model_description: `{provider}プロバイダーのデフォルトモデルが見つかりませんでした。この問題を\`/support discord\`で報告してください。`,
          success_title: `APIキーが設定されました`,
          success_description: `{provider}のAPIキーが正常に検証、暗号化、保存されました。`,
          success_with_model_description: `{provider}のAPIキーが正常に検証、暗号化、保存されました。モデルは自動的に\`{model_name}\`（このプロバイダーのデフォルト）に変更されました。`,
          custom_success_with_model_description: `カスタムのOpenAI互換エンドポイントが正常に保存されました。このエンドポイントへのリクエストでは \`{model_name}\` を使用します。`,
          novelai_success_with_model_description: `NovelAIのAPIキーが正常に検証、暗号化、保存されました。モデルは自動的に\`{model_name}\`に変更されました。⚠️ **絵文字とスタンプの使用は自動的に無効化されました**。NovelAIのコンテキストを安定させるためです。\`/config permissions\`でいつでも再有効化できます。`,
        },
        delete: {
          description: `現在設定されているAIプロバイダーのAPIキーを削除します。`,
          no_key_title: `APIキーが設定されていません`,
          no_key_description: `現在削除するAPIキーが設定されていません。`,
          success_title: `APIキーが削除されました`,
          success_description: `AIプロバイダーのAPIキーが正常に削除されました。新しいキーが設定されるまで、私のチャット機能は無効になります。`,
        },
        rotation: {
          description: `負荷分散とフェイルオーバー用のAPIキーローテーションを管理します。`,
          action_description: `アクションを選択：キーを追加するか、すべてのキーを削除`,
          action_add: `キーを追加`,
          action_purge: `すべてのキーを削除`,
          action_choice_purge: `すべてのキーを削除`,
          key_description: `ローテーションプールに追加するAPIキー（追加アクションに必要）`,
          // 検証エラー
          no_main_key_title: `メインAPIキーがありません`,
          no_main_key_description: `ローテーションキーを追加する前に、\`/config apikey set\`を使用してメインAPIキーを設定する必要があります。`,
          custom_provider_title: `サポートされていません`,
          custom_provider_description: `カスタムプロバイダーではAPIキーローテーションはサポートされていません。`,
          key_required_title: `キーが必要です`,
          key_required_description: `「追加」アクションを使用する場合は、APIキーを入力してください。`,
          // 成功メッセージ
          add_success_title: `ローテーションキーが追加されました`,
          add_success_description: `新しいAPIキーがローテーションプールに正常に追加されました。現在、{provider}に**{count}**個のローテーションキーがあります。キーはラウンドロビン順序で自動フェイルオーバーとともに使用されます。`,
          purge_success_title: `ローテーションキーが削除されました`,
          purge_success_description: `ローテーションプールから**{count}**個のキーが正常に削除されました。メインAPIキーのみが使用されます。`,
          // 情報メッセージ
          no_keys_title: `ローテーションキーがありません`,
          no_keys_description: `削除するローテーションキーがありません。メインAPIキーのみが設定されています。`,
        },
        help: {
          description: `カスタムプロバイダー（OpenAI互換エンドポイント）のセットアップ方法。`,
          title: `カスタムプロバイダーのセットアップ`,
          body: `Ollama・vLLM・LiteLLM・OneAPI・KoboldCPPなど、任意のOpenAI互換エンドポイントに接続できます。\n\n**エンドポイントURL**\nカスタムプロバイダーを選択する際に、APIキーフィールドにベースURLを入力してください。\n例: \`https://my-server.com/v1\`\n\`/chat/completions\` は自動で付加されます。自分で追加しないでください。\n本番環境では**HTTPS**かつ公開アクセス可能なURLが必要です（localhostやプライベートIPは不可）。\n\n**モデル名**\nURL入力後に表示される機能設定プロンプトで設定します。エンドポイントが期待する正確な名前を入力してください。例: Ollamaなら \`gemma3:latest\`、プロキシならそのモデルID。\nリクエストの \`model\` フィールドとして送信されます。\n\n**APIキー / Bearerトークン**\nオプションです。セットアップ後に \`/config apikey set\` で認証トークンを保存できます。\n設定した場合、\`Authorization: Bearer {token}\` として送信されます。\n認証不要なエンドポイントでは設定不要です。`,
        },
      },
      // カスタムプロバイダー設定
      custom: {
        // エンドポイントURLフィールドのヘルプテキスト（カスタムプロバイダーのAPIキーフィールドの代わりに表示）
        endpoint_url_label: `エンドポイントURL`,
        endpoint_url_description: `OpenAI互換エンドポイントのURLを入力してください（例：https://my-llm-server.com/v1 、開発環境では http://localhost:11434/v1）`,
        endpoint_url_placeholder: `https://my-llm-server.com/v1`,
        endpoint_url_invalid_title: `無効なエンドポイントURL`,
        endpoint_url_invalid_description: `カスタムエンドポイントの有効なHTTPまたはHTTPS URLを入力してください。`,
        endpoint_url_protocol_description: `URLはHTTPまたはHTTPSプロトコルを使用する必要があります。`,
        endpoint_url_https_required_description: `本番環境ではHTTPSが必要です。公開アクセス可能なHTTPSエンドポイントを使用してください（例：https://my-llm-server.com/v1）。`,
        endpoint_url_http_localhost_only_description: `HTTPは開発環境のlocalhost専用です。リモートサーバーにはHTTPSを使用してください。`,
        endpoint_url_localhost_blocked_description: `本番環境ではlocalhostエンドポイントは使用できません。公開アクセス可能なHTTPSエンドポイントを使用してください。`,
        endpoint_url_dns_failed_description: `ホスト名 \`{hostname}\` を解決できませんでした。サーバーが公開アクセス可能であり、URLが正しいことを確認してください。`,
        endpoint_url_private_address_description: `\`{address}\` はプライベートまたは予約済みIPアドレスです。公開アクセス可能なHTTPSエンドポイントを使用してください。`,
        // モデル名設定
        model_name_label: `モデル名（必須）`,
        model_name_description: `必須です。エンドポイントが期待する正確な上流モデル名を入力してください（例：「gpt-5.4」「gpt-5.3-codex」「gemma3:latest」）。`,
        model_name_placeholder: `例：gpt-5.4 または gemma3:latest`,
        model_name_required_description: `確認する前に正確なモデル名を設定してください。ChatMockなら \`gpt-5.4\` のような名前、Ollamaなら \`gemma3:latest\` のような正確なモデルタグを入力してください。`,
        // 機能設定モーダル
        modal_capabilities_title: `モデル機能の設定`,
        capabilities_prompt: `エンドポイントが期待する正確なモデル名を設定してから、そのモデルがサポートする機能を選択し、**確認**をクリックしてください:`,
        capability_tools_label: `関数呼び出し（ツール）?`,
        capability_tools_yes: `関数呼び出しをサポート`,
        capability_tools_no: `関数呼び出し非対応`,
        capability_images_label: `画像理解?`,
        capability_images_yes: `画像をサポート`,
        capability_images_no: `画像非対応`,
        capability_videos_label: `動画理解?`,
        capability_videos_yes: `動画をサポート`,
        capability_videos_no: `動画非対応`,
        capability_structoutput_label: `構造化出力?`,
        capability_structoutput_yes: `構造化出力をサポート`,
        capability_structoutput_no: `構造化出力非対応`,
        // 成功/エラーメッセージ
        setup_success_title: `カスタムエンドポイントが設定されました`,
        setup_success_description: `カスタムのOpenAI互換エンドポイントが正常に設定されました。`,
        capabilities_timeout: `モデル機能の設定がタイムアウトしました。もう一度お試しください。`,
        // セレクトメニューに表示されるプロバイダー説明
        provider_description: `任意のOpenAI互換エンドポイント（Ollama、vLLMなど）に接続`,
      },
      // プロバイダー設定の永続化 — 保存されたプロバイダー設定の切替/削除
      provider: {
        description: `保存されたプロバイダー設定を管理`,
        switch: {
          description: `AIプロバイダーを切り替えます（現在の設定を保存して簡単に復元可能）。`,
          modal_title: `プロバイダーの切替`,
          provider_label: `切替先プロバイダー`,
          provider_description: `切り替えるプロバイダーを選択してください。(保存済み)のプロバイダーは設定が保存されています。`,
          provider_placeholder: `プロバイダーを選択...`,
          api_key_label: `APIキー（任意）`,
          api_key_description: `保存済みキーを復元するには空欄のまま、新しいキーで上書きする場合は入力してください。`,
          api_key_description_with_custom: `保存済みを復元するには空欄のまま、新規カスタムの場合はOpenAIエンドポイントURLを入力してください。`,
          api_key_placeholder: `保存済みキーを使用するには空欄`,
          save_current_label: `現在の設定を保存しますか？`,
          save_current_description: `現在のプロバイダー設定を保存して、後で復元できるようにします。`,
          save_yes_label: `はい`,
          save_no_label: `いいえ`,
          saved_indicator: `(保存済み)`,
          // エラー状態
          first_time_no_key_title: `APIキーが必要です`,
          first_time_no_key_description: `**{provider}**の保存済み設定がありません。新しいプロバイダーに初めて切り替える場合は、APIキーを入力してください。`,
          // 成功状態
          success_title: `プロバイダーを切り替えました`,
          success_description: `**{provider}**に切り替えました。モデルは\`{model_name}\`になりました。`,
          success_restored_description: `保存済みの設定で**{provider}**に切り替えました。モデルは\`{model_name}\`になりました。{restored_details}`,
          // 復元設定サマリーのラベル
          restored_label: `復元済み`,
          no_restores_label: `復元データなし`,
          carried_over_note: `*その他の設定は現在の設定から引き継がれます。*`,
          skipped_overrides_note: `⚠️ {count}件のオーバーライドをスキップしました — チャンネルまたはペルソナが存在しません。`,
          config_label_chat_model: `チャットモデル`,
          config_label_vision_model: `ビジョンモデル`,
          config_label_image_model: `画像モデル`,
          config_label_embedding_model: `埋め込みモデル`,
          config_label_sampler_settings: `サンプラー設定`,
          config_label_fallback_models: `フォールバックモデル ({count})`,
          config_label_channel_overrides: `チャンネルオーバーライド ({count})`,
          config_label_persona_overrides: `ペルソナオーバーライド ({count})`,
          config_label_fallback_models_none: `フォールバックモデル`,
          config_label_channel_overrides_none: `チャンネルオーバーライド`,
          config_label_persona_overrides_none: `ペルソナオーバーライド`,
          config_label_custom_endpoint: `カスタムエンドポイント`,
          success_novelai_description: `**{provider}**に切り替えました。モデルは\`{model_name}\`になりました。⚠️ **絵文字とスタンプの使用は自動的に無効化されました**。NovelAIのコンテキストを安定させるためです。\`/config permissions\`でいつでも再有効化できます。`,
          success_zai_description: `**{provider}**に切り替えました。モデルは\`{model_name}\`になりました。`,
        },
        remove: {
          description: `保存されたプロバイダー設定を削除します。`,
          no_saved_title: `保存済み設定がありません`,
          no_saved_description: `削除する保存済みプロバイダー設定がありません。保存済み設定は「現在の設定を保存」を有効にして\`/config provider switch\`を使用すると作成されます。`,
          select_placeholder: `削除するプロバイダーを選択...`,
          success_title: `保存済み設定を削除しました`,
          success_description: `**{provider}**の保存済み設定を削除しました。次回このプロバイダーに切り替える際はAPIキーが必要です。`,
          confirm_title: `保存済み設定を削除しますか？`,
          confirm_description: `**{provider}**の保存済み設定を削除してもよろしいですか？保存されたAPIキーとモデル選択が削除されます。`,
        },
      },
      humanizer: {
        description: `私の応答がどれだけ「人間らしい」か設定します。カスタムプロンプトを設定するには \`/config sysprompt change\` を使用してください。`,
        modal_title: `ヒューマナイザーレベルの設定`,
        select_label: `ヒューマナイザーレベル`,
        select_description: `応答スタイルを選択してください（デフォルト: 1 ライト）。`,
        select_placeholder: `レベルを選択...`,
        choice_none: `0: なし (生のAI出力)`,
        choice_light: `1: ライト（デフォルト、プロンプト注入）`,
        choice_medium: `2: ミディアム (タイピングシミュレーション＆チャンキング)`,
        choice_heavy: `3: ヘビー (小文字＆句読点なし)`,
        desc_none: `人間化なし。フォーマルなトーンと構造の標準的なAI応答。`,
        desc_light: `システムプロンプトを追加。絵文字を制限（0-2個）、簡潔な応答を優先。\`/config sysprompt change\` でカスタマイズ可能。`,
        desc_medium: `ライト機能 + タイピングシミュレーションと自然な流れのためのメッセージチャンキングの改善。`,
        desc_heavy: `全機能 + カジュアルなテキスト処理（小文字、句読点の削減）でインフォーマルなトーンに。`,
        invalid_value_description: `ヒューマナイザーレベルは {min} から {max} の間でなければなりません。`,
        already_set_title: `ヒューマナイザーは既に設定済みです`,
        already_set_description: `ヒューマナイザーレベルは既に \`{value}\` に設定されています。`,
        success_title: `ヒューマナイザーレベルが更新されました`,
        success_description: `ヒューマナイザーレベルが \`{previous_value}\` から \`{value}\` に変更されました。`,
      },
      cooldown: {
        description: `メッセージトリガーのクールダウンタイプと時間をまとめて設定します。`,
        cooldown_type_description: `クールダウンの適用方法（オフ / ユーザーごと / チャンネルごと / サーバー全体）。`,
        cooldown_length_description: `クールダウン時間（秒、1-86400）。`,
        cooldown_type_choice_0: `オフ`,
        cooldown_type_choice_1: `ユーザーごと`,
        cooldown_type_choice_2: `チャンネルごと`,
        cooldown_type_choice_3: `サーバー全体`,
        cooldown_type_choice_4: `厳密サーバー全体`,
        invalid_type_title: `無効なクールダウンタイプ`,
        invalid_type_description: `選択されたクールダウンタイプが無効です。有効なオプションを選択してください。`,
        invalid_length_title: `無効な時間`,
        invalid_length_description: `時間は {min} から {max} 秒（24時間）の間で指定してください。`,
        already_set_title: `既に設定済み`,
        already_set_description: `クールダウン設定は既に **{type}**（**{length}** 秒）です。`,
        success_title: `クールダウンを更新しました`,
        success_description: `クールダウンを **{previous_type}**（**{previous_length}** 秒）から **{type}**（**{length}** 秒）に更新しました。`,
        success_disabled_title: `クールダウンが無効化されました`,
        success_disabled_description: `クールダウンを **{previous_type}**（**{previous_length}** 秒）から **{type}**（**{length}** 秒）に更新しました。メッセージトリガーのクールダウンは現在 **無効** です。`,
        type: {
          description: `メッセージトリガーのクールダウンタイプを設定します。`,
          modal_title: `クールダウンタイプ`,
          select_label: `タイプ`,
          select_description: `クールダウンの適用方法を選択`,
          select_placeholder: `クールダウンタイプを選択...`,
          choice_off: `オフ`,
          choice_per_user: `ユーザーごと`,
          choice_per_channel: `チャンネルごと`,
          choice_server_wide: `サーバー全体`,
          choice_strict_server_wide: `厳密サーバー全体`,
          desc_off: `メッセージトリガーにクールダウンなし`,
          desc_per_user: `各ユーザーが独自のクールダウンを持つ（管理者は免除）`,
          desc_per_channel: `各チャンネルが独自のクールダウンを持つ（管理者は免除）`,
          desc_server_wide: `全員が待機（管理者は免除）`,
          desc_strict_server_wide: `全員が待機（例外なし）`,
          invalid_value_description: `無効なクールダウンタイプが選択されました。有効なオプションを選択してください。`,
          success_title: `クールダウンタイプが更新されました`,
          success_description: `クールダウンタイプが **{previous_value}** から **{value}** に変更されました。`,
          success_disabled_title: `クールダウンが無効化されました`,
          success_disabled_description: `クールダウンタイプが **{previous_value}** から **{value}** に変更されました。メッセージトリガーのクールダウンが無効になりました。`,
          already_set_title: `既に設定済み`,
          already_set_description: `クールダウンタイプは既に **{value}** に設定されています。`,
        },
        length: {
          description: `メッセージトリガーのクールダウン時間を設定します。`,
          seconds_description: `秒単位の時間（1-86400）`,
          success_title: `クールダウン時間が更新されました`,
          success_description: `クールダウン時間を **{length}** 秒に設定しました。`,
          success_disabled_title: `時間が設定されました（クールダウンオフ）`,
          success_disabled_description: `時間を **{length}** 秒に設定しましたが、クールダウンは現在 **無効** です。有効にするには \`/config cooldown\` を使用してください。`,
          already_set_title: `既に設定済み`,
          already_set_description: `クールダウン時間は既に **{length}** 秒です。`,
          invalid_range_title: `無効な時間`,
          invalid_range_description: `時間は {min} から {max} 秒（24時間）の間でなければなりません。`,
        },
      },
      selfreply: {
        description: `ペルソナ同士の自己返信チェーンを管理します（デフォルト: 3）。`,
        limit_description: `許可する自己返信回数 (0-10、0で無効、デフォルト: 3)`,
        limit: {
          description: `自己返信チェーンの上限回数を設定します（デフォルト: 3）。`,
          limit_description: `許可する自己返信回数 (0-10、0で無効、デフォルト: 3)`,
          invalid_range_title: `無効な上限値`,
          invalid_range_description: `上限は {min} 〜 {max} の範囲で指定してください。`,
          already_set_title: `既に設定済み`,
          already_set_description: `自己返信上限はすでに **{limit}** に設定されています。`,
          success_title: `自己返信上限を更新しました`,
          success_description: `自己返信チェーンの上限を **{limit}** に設定しました。`,
          success_disabled_title: `自己返信を無効化しました`,
          success_disabled_description: `自己返信チェーンを無効にしました。`,
        },
      },
      sendlimit: {
        description: `1回の応答で送信するメッセージ数の上限を設定します（デフォルト: 0 = 無制限）。`,
        limit_description: `応答あたりの最大メッセージ数 (0-40、0で無制限、デフォルト: 0)`,
        invalid_range_title: `無効な上限値`,
        invalid_range_description: `上限は {min} 〜 {max} の範囲で指定してください。`,
        already_set_title: `既に設定済み`,
        already_set_description: `送信メッセージ上限はすでに **{limit}** に設定されています。`,
        success_title: `送信上限を更新しました`,
        success_description: `応答は **{limit}** メッセージに制限されます。上限に達すると、文の区切りで自然に停止します。`,
        success_disabled_title: `送信上限を無効化しました`,
        success_disabled_description: `送信メッセージ上限を解除しました。応答は制限されなくなります。`,
      },
      selfdebug: {
        description: `私が送信した診断埋め込みをコンテキストに取り込むか切り替えます。`,
        set_description: `セルフデバッグ埋め込み取り込みを有効または無効にします。`,
        already_set_title: `セルフデバッグは既に設定済みです`,
        already_enabled_description: `セルフデバッグは既に**有効**です。`,
        already_disabled_description: `セルフデバッグは既に**無効**です。`,
        success_title: `セルフデバッグを更新しました`,
        enabled_success: `セルフデバッグを**有効**にしました。私のエラー埋め込みと診断埋め込みを [System: ...] メッセージとしてコンテキストに取り込みます。`,
        disabled_success: `セルフデバッグを**無効**にしました。私のエラー埋め込みと診断埋め込みはコンテキストに取り込みません。`,
      },
      maxmsgfetch: {
        description: `コンテキスト取得メッセージ数を設定します (20-100、デフォルト: 80)。`,
        limit_description: `コンテキスト取得メッセージ数 (20-100、デフォルト: 80)。`,
        limit: {
          description: `コンテキスト取得メッセージ数の上限を設定します（デフォルト: 80）。`,
          limit_description: `コンテキスト取得メッセージ数 (20-100、デフォルト: 80)。`,
          invalid_range_title: `無効な上限値`,
          invalid_range_description: `上限は {min} 〜 {max} の範囲で指定してください。`,
          already_set_title: `既に設定済み`,
          already_set_description: `メッセージ取得上限はすでに **{limit}** に設定されています。`,
          success_title: `メッセージ取得上限を更新しました`,
          success_description: `今後はコンテキスト用に最大 **{limit}** 件のメッセージを取得します。`,
        },
      },
      multitrigger: {
        description: `1つのメッセージで起動できるペルソナ数を管理します（デフォルト: 3）。`,
        limit_description: `1メッセージで起動できるペルソナ上限 (1-10、デフォルト: 3)`,
        limit: {
          description: `メッセージごとの最大起動ペルソナ数を設定します（デフォルト: 3）。`,
          limit_description: `1メッセージで起動できるペルソナ上限 (1-10、デフォルト: 3)`,
          invalid_range_title: `無効な上限値`,
          invalid_range_description: `上限は {min} 〜 {max} の範囲で指定してください。`,
          already_set_title: `既に設定済み`,
          already_set_description: `マルチトリガー上限はすでに **{limit}** に設定されています。`,
          success_title: `マルチトリガー上限を更新しました`,
          success_description: `メッセージごとのペルソナ起動上限を **{limit}** に設定しました。`,
        },
      },
      voice: {
        description: `ペルソナごとの音声設定を管理します。`,
        transcripts: {
          description: `音声トランスクリプトのチャットモードを切り替えます。`,
          set_description: `有効にするとトランスクリプトをチャットメッセージとして投稿します。無効にすると内部キャッシュを使用します。`,
          already_set_title: `既に設定済み`,
          already_enabled_description: `このサーバーでは音声トランスクリプトのチャットモードは既に有効になっています。`,
          already_disabled_description: `このサーバーでは音声トランスクリプトのチャットモードは既に無効になっています。`,
          success_title: `音声トランスクリプトモードを更新しました`,
          enabled_success: `音声トランスクリプトのチャットモードが**有効**になりました。音声メッセージはトランスクリプトされ、Webhookを通じてチャットメッセージとして投稿されます。音声ファイルはAIに直接渡されません。`,
          disabled_success: `音声トランスクリプトのチャットモードが**無効**になりました。トランスクリプトは従来通り内部で処理されます。`,
        },
        elevenlabs: {
          description: `ペルソナに使うElevenLabs音声を選択します。`,
          select_persona_title: `音声を設定するペルソナを選択`,
          no_key_title: `ElevenLabs APIキーが設定されていません`,
          no_key_description: `ペルソナの音声を選ぶにはElevenLabsキーが必要です。まず \`/optionalkey elevenlabs set\` で設定してください。`,
          voice_fetch_failed_title: `音声一覧を取得できませんでした`,
          voice_fetch_failed_description: `このサーバーで利用できるElevenLabs音声を読み込めませんでした。設定済みキーを確認して、もう一度お試しください。`,
          no_voices_title: `利用可能な音声がありません`,
          no_voices_description: `設定されているElevenLabsアカウントから利用可能な音声が返されませんでした。`,
          modal_title: `ElevenLabs音声を選択`,
          select_label: `音声`,
          select_description: `このペルソナが音声メッセージ生成で使う音声を選択してください。`,
          select_placeholder: `音声を選択...`,
          clear_choice_label: `音声を無効化`,
          clear_choice_description: `このペルソナの現在のElevenLabs音声設定を削除します。`,
          voice_available_description: `利用可能な音声`,
          success_title: `ペルソナの音声を更新しました`,
          success_description: `**{persona}** は今後、ElevenLabs音声メッセージで **{voice}** を使用します。`,
          cleared_title: `ペルソナの音声を解除しました`,
          cleared_description: `**{persona}** のElevenLabs音声設定を削除しました。`,
        },
      },
      model: {
        text: {
          description: `私が使用する基盤となるAIモデルを変更します。`,
          modal_title: `AIモデルの選択`,
          select_label: `AIモデル`,
          select_description: `私が使用するAIモデルを選択してください。無料でないモデルの価格については、各AIプロバイダーの公式サイトをご確認ください。`,
          select_placeholder: `モデルを選択...`,
          no_api_key_title: `APIキーが設定されていません`,
          no_api_key_description: `モデルを変更する前にAPIキーを設定する必要があります。まず \`/config apikeyset\` を使用してAPIキーを設定してください。`,
          no_models_title: `モデルが見つかりません`,
          no_models_description: `データベースから利用可能なAIモデルを読み込めませんでした。`,
          invalid_model_title: `無効なモデル`,
          invalid_model_description: `選択されたモデル名は無効か、利用できません。`,
          already_selected_title: `モデルは既に選択済みです`,
          already_selected_description: `私は既に \`{model_name}\` モデルを使用しています。`,
          validating_api_key_compatibility_title: `APIキーを検証中`,
          validating_api_key_compatibility: `新しいプロバイダーとのAPIキー互換性を検証中...`,
          api_key_incompatible_title: `APIキーに互換性がありません`,
          api_key_incompatible_description: `現在のAPIキーは{provider}の{model_name}モデルと互換性がありません。\`/config apikeyset\`を使用して{provider}の有効なAPIキーを設定してください。`,
          validation_error_title: `検証エラー`,
          validation_error_description: `APIキーの互換性検証中にエラーが発生しました。もう一度お試しください。`,
          success_title: `モデルが更新されました`,
          success_description: `これからは \`{model_name}\` モデルを使用します（以前は \`{previous_model}\`）。`,
          // カスタムプロバイダー再設定メッセージ
          custom_updated_title: `カスタムモデルの機能が更新されました`,
          custom_updated_description: `カスタムモデルが再設定されました。\n\n**モデル名:** \`{model_name}\`\n**有効な機能:** {capabilities}`,
          // スコープオプションラベルと成功メッセージ (scope = global | channel | persona)
          scope_description: `このモデル変更のスコープを設定します（グローバル、チャンネル、またはペルソナ）。`,
          scope_global: `グローバル（サーバーデフォルト）`,
          scope_channel: `チャンネル（このチャンネルのみ）`,
          scope_persona: `ペルソナ（特定のペルソナのみ）`,
          scope_set_channel_success: `{channel} のモデルを **{model}** に設定しました`,
          scope_set_persona_success: `**{persona}** のモデルを **{model}** に設定しました`,
          // Other-model configuration
          other_model_prompt_title: `カスタム OpenRouter モデルの設定`,
          other_model_prompt_description: `**other-model** を選択しました。\n\n下のボタンをクリックして、OpenRouter モデルのコードネームを入力してください（例：\`xai/grok-2\`、\`openrouter/free\`、\`nvidia/nemotron-4-340b-instruct\`）。`,
          other_model_modal_title: `OpenRouter モデルを入力`,
          other_model_model_label: `OpenRouter モデルコードネーム`,
          other_model_model_placeholder: `xai/grok-2`,
          other_model_validating_title: `モデルを検証中`,
          other_model_validating_description: `OpenRouter で \`{model_name}\` の機能を取得しています...`,
          other_model_validation_failed_title: `モデルが見つかりません`,
          other_model_validation_failed_description: `OpenRouter で \`{model_name}\` が見つかりませんでした。モデルIDが正しいか確認して再試行してください。`,
          other_model_configured_title: `カスタムモデルの設定が完了`,
          other_model_configured_description: `カスタム OpenRouter モデルが \`{model_name}\` に設定されました。\n\n**検出された機能:** {capabilities}`,
        },
        embedding: {
          description: `文書検索に使用する埋め込みモデルを変更します。`,
          modal_title: `埋め込みモデルを選択`,
          select_label: `埋め込みモデル`,
          select_description: `文書検索に使用する埋め込みモデルを選択してください。`,
          select_placeholder: `モデルを選択...`,
          no_api_key_title: `APIキーが設定されていません`,
          no_api_key_description: `埋め込みモデルを変更するにはAPIキーが必要です。\`/config apikey set\`を使用してください。`,
          no_models_title: `埋め込みモデルがありません`,
          no_models_description: `プロバイダー {provider} で利用可能な埋め込みモデルが見つかりませんでした。`,
          invalid_model_title: `無効なモデル`,
          invalid_model_description: `選択された埋め込みモデルは無効です。`,
          already_selected_title: `既に選択されています`,
          already_selected_description: `既に \`{model_name}\` を使用しています。`,
          reembed_started_title: `再埋め込み中`,
          reembed_started_description: `新しいモデルで文書の埋め込みを再生成しています。しばらくお待ちください...`,
          success_title: `埋め込みモデルを更新しました`,
          success_description: `埋め込みモデルを \`{model_name}\` に変更しました（以前: \`{previous_model}\`）。`,
          current_none: `なし`,
        },
        fallback: {
          description: `プライマリモデルが失敗した場合に使用するバックアップモデルを設定します。`,
          modal_title: `フォールバックモデルの設定`,
          slot_1_label: `フォールバックモデル1（必須）`,
          slot_2_label: `フォールバックモデル2`,
          slot_3_label: `フォールバックモデル3`,
          slot_4_label: `フォールバックモデル4`,
          slot_5_label: `フォールバックモデル5`,
          select_placeholder: `モデルを選択...`,
          no_models_title: `モデルが見つかりません`,
          no_models_description: `現在のプロバイダーで利用可能なモデルがありません。`,
          custom_provider_title: `非対応`,
          custom_provider_description: `カスタムプロバイダーではフォールバックモデルはサポートされていません。`,
          primary_conflict_title: `選択が無効です`,
          primary_conflict_description: `選択したフォールバックモデルの一つ以上がサーバーのプライマリモデル \`{model}\` と一致しています。別のモデルを選択してください。`,
          success_title: `フォールバックモデルを更新しました`,
          success_description: `フォールバック順:\n{model_list}`,
          cleared_title: `フォールバックモデルをクリアしました`,
          cleared_description: `このサーバーにフォールバックモデルは設定されていません。`,
        },
        image: {
          description: `このサーバーの画像生成モデルを変更します。`,
          modal_title: `画像生成モデルの選択`,
          select_label: `画像モデル`,
          select_description: `画像生成モデルを選択してください。価格については各AIプロバイダーをご確認ください。`,
          select_placeholder: `画像モデルを選択...`,
          no_api_key_title: `APIキーが設定されていません`,
          no_api_key_description: `画像モデルを変更する前にAPIキーを設定する必要があります。`,
          no_models_title: `画像モデルが利用できません`,
          no_models_description: `現在のテキストモデルプロバイダー（{provider}）は画像生成をサポートしていません。まず \`/config apikey set\` を使用してGoogleまたはOpenRouterに切り替えてください。`,
          invalid_model_description: `選択された画像モデルは無効か、利用できません。`,
          already_selected_title: `モデルは既に選択済みです`,
          already_selected_description: `既に \`{model_name}\` 画像モデルを使用しています。`,
          success_title: `画像モデルが更新されました`,
          success_description: `画像生成には \`{model_name}\` モデルを使用します（以前は \`{previous_model}\`）。`,
          current_none: `なし`,
        },
        vision: {
          description: `チャットモデルが画像を見られない場合に画像分析用のビジョンモデルを設定します。`,
          modal_title: `ビジョンモデルの選択`,
          select_label: `ビジョンモデル`,
          select_description: `チャットモデルの代わりに画像を分析するビジョン対応モデルを選択してください。`,
          select_placeholder: `ビジョンモデルを選択...`,
          no_api_key_title: `APIキー未設定`,
          no_api_key_description: `ビジョンモデルを設定する前にAPIキーを設定してください。\`/config apikey set\` を使用してください。`,
          no_models_title: `ビジョンモデルがありません`,
          no_models_description: `現在のプロバイダー（{provider}）にはビジョン対応モデルがありません。先にビジョンモデルのあるプロバイダーに切り替えてください。`,
          invalid_model_title: `無効なモデル`,
          invalid_model_description: `選択されたビジョンモデルは無効または利用できません。`,
          already_selected_title: `モデルは既に選択済みです`,
          already_selected_description: `既に \`{model_name}\` をビジョンモデルとして使用しています。`,
          not_needed_title: `ビジョンモデルは不要です`,
          not_needed_description: `現在のチャットモデル（\`{model_name}\`）は既に画像ビジョンをサポートしています。別のビジョンモデルはビジョン非対応のチャットモデルにのみ有用です。`,
          success_title: `ビジョンモデルが更新されました`,
          success_description: `ビジョン非対応のチャットモデルは \`{model_name}\` を使用して \`analyze_image\` ツールで画像を分析します。`,
          success_no_tools_description: `ビジョンモデルを \`{model_name}\` に設定しましたが、現在のチャットモデル（\`{chat_model}\`）は**ツール呼び出し**に対応していません。ビジョンモデルは \`analyze_image\` ツールが必要です — ツール対応のチャットモデルに切り替えてください。`,
          cleared_title: `ビジョンモデルを削除しました`,
          cleared_description: `ビジョンモデルが削除されました。ビジョン非対応のチャットモデルは画像を分析できなくなります。`,
          clear_option: `なし（ビジョンツールを無効化）`,
        },
      },
      rename: {
        description: `このサーバーでの私の名前を変更します。`,
        modal_title: `ペルソナ名の変更`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `名前を変更するペルソナを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        new_name_input_label: `新しい名前`,
        new_name_input_description: `新しい名前を入力してください（2〜32文字）。`,
        new_name_input_placeholder: `新しいペルソナ名を入力...`,
        option_description: `私の新しい名前（2〜32文字）。`,
        invalid_length_title: `無効な名前の長さ`,
        invalid_length: `名前は2〜32文字でなければなりません。`,
        already_set_title: `名前は既に設定済みです`,
        already_set_description: `私の名前は既に \`{nickname}\` に設定されています。`,
        success_title: `名前が更新されました`,
        success_description: `私の名前が \`{old_nickname}\` から \`{new_nickname}\` に変更されました。`,
        success_with_trigger_description: `私の名前が \`{old_nickname}\` から \`{new_nickname}\` に変更されました。トリガーワードもそれに合わせて更新されました。`,
        success_with_discord_description: `私の名前が \`{old_nickname}\` から \`{new_nickname}\` に変更され、サーバーのニックネームも更新されました！`,
        success_with_trigger_and_discord_description: `私の名前が \`{old_nickname}\` から \`{new_nickname}\` に変更されました。トリガーワードとサーバーのニックネームが更新されました！`,
        nickname_update_failed_footer: `注：サーバーのニックネーム更新に失敗しました（「ニックネームの変更」権限が必要な場合があります）。`,
        partial_success_title: `名前は更新されましたが問題あり`,
        partial_success_description: `私の名前は \`{new_nickname}\` に変更されましたが、一部のトリガーワードの更新に失敗しました。`,
      },
      setup: {
        description: `初期設定プロセスを開始します。AIプロバイダーとパーソナリティを設定します。`,
        no_presets_found: `エラー: あなたの言語用の人格プリセットが見つかりません。設定を続行できません。`,
        modal_title: `初期の設定`,
        api_provider_label: `APIプロバイダー`,
        api_provider_description: `お好みのLLMのプロバイダーを選択してください`,
        api_provider_placeholder: `選択してください...`,
        api_key_label: `APIキー`,
        api_key_description: `選択したLLMプロバイダーのAPIキーを入力してください。このキーは安全に保存されます。取得方法が不明な場合は、\`/help apikey\`コマンドを使用してください。`,
        api_key_description_with_custom: `APIキー、またはCustomの場合はOpenAIエンドポイントURL（例：http://localhost:11434/v1）`,
        api_key_placeholder: `このキーは誰とも共有しないでください`,
        preset_label: `人格プリセット`,
        preset_description: `人格プリセットを選択してください`,
        preset_placeholder: `人格を選択...`,
        humanizer_label: `人間らしさの度合い`,
        humanizer_description: `どれくらい「人間らしく」返信すべきですか？`,
        humanizer_placeholder: `人間らしさのレベルを選択...`,
        humanizer_option_none_label: `なし`,
        humanizer_option_none_desc: `生のAI出力。遅延なし、完全な句読点、即時応答。`,
        humanizer_option_light_label: `軽`,
        humanizer_option_light_desc: `基本的なガイダンス：絵文字0〜2個、簡潔に応答。タイピングシミュレーションなし。`,
        humanizer_option_default_label: `デフォルト`,
        humanizer_option_default_desc: `バランス型：リアルなタイピングインジケーターとメッセージ間の思考ポーズ。`,
        humanizer_option_heavy_label: `重`,
        humanizer_option_heavy_desc: `最大：タイピング遅延付きの文単位のチャンク化、カジュアルな小文字テキスト。`,
        humanizer_field: `人間らしさ`,
        humanizer_invalid: `無効な人間らしさの度合いです。なし、軽、デフォルト、または重を選択してください。`,
        timezone_label: `タイムゾーンオフセット`,
        timezone_description: `時間単位のUTCオフセット。例：8または+8（シンガポール）、-5（ニューヨーク）、0（ロンドン）。空欄の場合はUTC。`,
        timezone_placeholder: `例：8、-5、0`,
        timezone_invalid_format: `エラー: 無効なタイムゾーン形式です。8、-5、0のような数値を入力してください。入力値: {provided}`,
        timezone_out_of_range: `エラー: タイムゾーンオフセットは{min}から{max}の間でなければなりません。入力値: {provided}`,
        api_key_invalid: `エラー: 提供されたAPIキーは短すぎるか無効です。`,
        api_key_validating: `APIキーを検証中...`,
        api_key_invalid_api: `エラー: プロバイダーがAPIキーを拒否しました。正しいか確認してください。`,
        preset_invalid: `エラー: 無効なペルソナ名です。利用可能なペルソナ名を正確に入力してください: {available}`,
        config_invalid: `エラー: 内部設定の検証に失敗しました。これを報告してください。`,
        setup_failed_description: `エラー: 初期設定構成をデータベースに保存できませんでした。もう一度お試しください。`,
        modal_values_missing: `エラー: 必須入力項目の一部がセットアップフォームから受信されませんでした。もう一度セットアップコマンドをお試しください。`,
        provider_invalid: `エラー: 無効なAPIプロバイダーが選択されました。利用可能なオプションから選択してください。`,
        preset_not_found: `エラー: 選択されたペルソナがデータベースに見つかりませんでした。もう一度お試しください。`,
        success_title: `🟢 設定完了！`,
        success_desc: `このサーバー用に設定が完了しました。私の設定を変更するには、\`/config\`と\`/server\`コマンドを使用してください。任意ですが推奨：\`/server initialize\` コマンドで絵文字・スタンプのメタデータを最適化できます。データの管理や削除は\`/data\`でいつでも可能です。概要は以下の通りです:`,
        success_desc_with_model: `このサーバー用に設定が完了しました。使用モデルは \`{model_name}\`（このプロバイダーのデフォルト）です。私の設定を変更するには、\`/config\`と\`/server\`コマンドを使用してください。任意ですが推奨：\`/server initialize\` コマンドで絵文字・スタンプのメタデータを最適化できます。データの管理や削除は\`/data\`でいつでも可能です。概要は以下の通りです:`,
        success_desc_dm: `このダイレクトメッセージ用に設定が完了しました。データの管理や削除は\`/data\`でいつでも可能です。概要は以下の通りです:`,
        success_desc_dm_with_model: `このダイレクトメッセージ用に設定が完了しました。使用モデルは \`{model_name}\`（このプロバイダーのデフォルト）です。データの管理や削除は\`/data\`でいつでも可能です。概要は以下の通りです:`,
        next_steps_title: `🟢 私に何ができる？`,
        next_steps_description: `{helpFeatures}で全機能を確認するか、チャットで直接聞いてみてください！使えるスラッシュコマンドも教えられます。`,
        novelai_expressions_warning_field: `⚠️ 表現機能の無効化`,
        novelai_expressions_warning_value: `NovelAIのコンテキストを安定させるため、絵文字とスタンプの使用が自動的に無効化されました。でいつでも再有効化できます。`,
        preset_field: `人格プリセット`,
        name_field: `私の名前`,
        dm_context_explanation_title: `ダイレクトメッセージについて`,
        dm_context_explanation: `このダイレクトメッセージでも「サーバー」として参照します。つまり、すべての「サーバー」機能が同じように動作しますが、私たちだけのプライベートな空間です！このダイレクトメッセージを私との1対1サーバーと考えてください。「サーバーメモリー」はここでのみの私の記憶です。`,
        already_setup_title: `既に設定済みです`,
        already_setup_description: `このサーバーでは既に設定が完了しています。設定を変更するには、\`/config humanizer\`、\`/config temperature\`、\`/teach attribute\`などの他のコマンドを使用してください。

				プロバイダーを変更したい場合は、\`/config apikeyset\`コマンドを使用してください。`,
      },
      params: {
        description: `AI生成品質のサンプリングパラメーターを調整します。`,
        temperature: {
          description: `応答の創造性/ランダム性を設定します（0〜2.0、デフォルト: 1.0）。`,
          value_description: `0（決定的）から2.0（非常にランダム）の間の値。デフォルト: 1.0。`,
          invalid_value_title: `無効なTemperature`,
          invalid_value_description: `Temperatureは {min} から {max} の間でなければなりません。`,
          already_set_title: `Temperatureは既に設定済みです`,
          already_set_description: `Temperatureは既に \`{temperature}\` に設定されています。`,
          success_title: `Temperatureが更新されました`,
          success_description: `LLMのTemperatureが \`{previous_temperature}\` から \`{temperature}\` に変更されました。\n**対応プロバイダー:** Google、OpenRouter、NovelAI、DeepSeek、Z.ai、Custom、NVIDIA NIM`,
        },
        "top-p": {
          description: `Top-P（核サンプリング）のしきい値を設定します（デフォルト: 0.95）。`,
          value_description: `サンプリングする確率質量（0.0=非常に制限的、1.0=完全分布）。デフォルト: 0.95。`,
          invalid_value_title: `無効なTop-P値`,
          invalid_value_description: `Top-Pは {min} から {max} の間でなければなりません。`,
          already_set_title: `Top-Pは既に設定済みです`,
          already_set_description: `Top-Pは既に \`{top_p}\` に設定されています。`,
          success_title: `Top-Pが更新されました`,
          success_description: `Top-Pが \`{previous_top_p}\` から \`{top_p}\` に変更されました。\n**対応プロバイダー:** Google、OpenRouter、NovelAI、DeepSeek、Z.ai、NVIDIA NIM`,
        },
        "top-k": {
          description: `Top-K（候補トークン数）の上限を設定します（デフォルト: 0）。`,
          value_description: `サンプリングするトークン数（0=無効、最大40）。デフォルト: 0。`,
          invalid_value_title: `無効なTop-K値`,
          invalid_value_description: `Top-Kは {min} から {max} の間でなければなりません。`,
          already_set_title: `Top-Kは既に設定済みです`,
          already_set_description: `Top-Kは既に \`{top_k}\` に設定されています。`,
          success_title: `Top-Kが更新されました`,
          success_description: `Top-Kが \`{previous_top_k}\` から \`{top_k}\` に変更されました。\n**対応プロバイダー:** Google、OpenRouter、NovelAI、DeepSeek、Z.ai、NVIDIA NIM`,
        },
        "frequency-penalty": {
          description: `繰り返しトークンへの頻度ペナルティを設定します（デフォルト: 0.0）。`,
          value_description: `頻出トークンへのペナルティ（-2.0〜2.0、2.0は1.99で保存）。デフォルト: 0.0。`,
          invalid_value_title: `無効なFrequency Penalty`,
          invalid_value_description: `Frequency penaltyは {min} から {max} の間でなければなりません。`,
          already_set_title: `Frequency Penaltyは既に設定済みです`,
          already_set_description: `Frequency penaltyは既に \`{frequency_penalty}\` に設定されています。`,
          success_title: `Frequency Penaltyが更新されました`,
          success_description: `Frequency penaltyが \`{previous_frequency_penalty}\` から \`{frequency_penalty}\` に変更されました。\n**対応プロバイダー:** OpenRouter、NovelAI、DeepSeek、Z.ai、NVIDIA NIM`,
        },
        "presence-penalty": {
          description: `繰り返しトピックへの存在ペナルティを設定します（デフォルト: 0.0）。`,
          value_description: `既出トピックへのペナルティ（-2.0〜2.0、2.0は1.99で保存）。デフォルト: 0.0。`,
          invalid_value_title: `無効なPresence Penalty`,
          invalid_value_description: `Presence penaltyは {min} から {max} の間でなければなりません。`,
          already_set_title: `Presence Penaltyは既に設定済みです`,
          already_set_description: `Presence penaltyは既に \`{presence_penalty}\` に設定されています。`,
          success_title: `Presence Penaltyが更新されました`,
          success_description: `Presence penaltyが \`{previous_presence_penalty}\` から \`{presence_penalty}\` に変更されました。\n**対応プロバイダー:** OpenRouter、NovelAI、DeepSeek、Z.ai、NVIDIA NIM`,
        },
        "min-p": {
          description: `Min-P（最小確率）のしきい値を設定します（デフォルト: 0.0）。`,
          value_description: `上位トークンに対する最小トークン確率（0.0=無効、1.0=最も制限的）。デフォルト: 0.0。`,
          invalid_value_title: `無効なMin-P値`,
          invalid_value_description: `Min-Pは {min} から {max} の間でなければなりません。`,
          already_set_title: `Min-Pは既に設定済みです`,
          already_set_description: `Min-Pは既に \`{min_p}\` に設定されています。`,
          success_title: `Min-Pが更新されました`,
          success_description: `Min-Pが \`{previous_min_p}\` から \`{min_p}\` に変更されました。\n**対応プロバイダー:** OpenRouter、NovelAI、DeepSeek、Z.ai、NVIDIA NIM`,
        },
      },
      logitbias: {
        description: `対応モデル向けのlogit bias項目を管理します。`,
        add: {
          description: `共通のbias値で、カンマ区切りのlogit bias項目を追加します。`,
          modal_title: `Logit Biasを追加`,
          terms_label: `単語 / トークンID`,
          terms_description: `カンマ区切りで入力。単語は現在のモデル向けにトークン化され、モデル変更時に再計算されます。例: Sorry, apology, 50256`,
          terms_placeholder: `例: Sorry, apology, 50256`,
          bias_label: `Bias値`,
          bias_description: `-100〜100の数値。例: -100`,
          bias_placeholder: `例: -100`,
          empty_terms_title: `項目がありません`,
          empty_terms_description: `少なくとも1つ、カンマ区切りの単語またはトークンIDを入力してください。`,
          term_too_long_title: `項目が長すぎます`,
          term_too_long_description: `各項目は最大{max_length}文字までです。`,
          invalid_bias_title: `無効なBias値`,
          invalid_bias_description: `Biasは {min} から {max} の数値でなければなりません。`,
          already_set_title: `変更はありません`,
          already_set_description: `入力された項目はすべて、同じbias値で既に保存されています。`,
          success_title: `Logit Biasを更新しました`,
          success_description: `新規 **{added_count}** 件を追加し、既存 **{updated_count}** 件を更新しました。\n保存合計: **{total_count}** 件\n現在のモデルで実行時に使える項目: **{runtime_ready_count}** 件`,
        },
        remove: {
          description: `保存済みのlogit bias項目を削除します。`,
          clearall_description: `モーダルを開かずに、保存済みのlogit bias項目をすべて削除します。`,
          modal_title: `Logit Biasを削除`,
          checkbox_label: `Logit Bias項目`,
          checkbox_label_continued: `Logit Bias項目（続き）`,
          checkbox_description: `削除したい項目のチェックを外してください。`,
          none_title: `Logit Bias項目はありません`,
          none_description: `このサーバーには保存済みのlogit bias項目がありません。`,
          select_page_title: `Logit Biasページを選択`,
          select_page_description: `このサーバーには保存済みのlogit bias項目が **{total_entries}** 件あり、**{total_pages}** ページに分かれています。編集するページを選んでください。`,
          too_many_title: `Logit Biasページが多すぎます`,
          too_many_description: `このサーバーには保存済みのlogit bias項目が **{total_entries}** 件あり、**{total_pages}** ページに分かれています。現在のページ選択UIは **{max_pages}** ページまで対応しています。`,
          no_removals_title: `削除された項目はありません`,
          no_removals_description: `どの項目も未チェックになっていません。保存済みのlogit bias項目は変更されていません。`,
          success_title: `Logit Bias項目を更新しました`,
          success_description: `**{removed_count}** 件を削除しました。保存済みの項目は **{remaining_count}** 件残っています。`,
          clearall_success_title: `Logit Biasをクリアしました`,
          clearall_success_description: `保存済みのlogit bias項目をすべて削除しました（**{removed_count}** 件）。`,
        },
        upload: {
          description: `SillyTavern形式のlogit bias JSONをアップロードします。`,
          file_description: `text と value フィールドを持つ logit bias オブジェクトの .json ファイル。`,
          invalid_file_title: `無効なファイル`,
          invalid_format: `添付ファイルはJSONファイルでなければなりません。`,
          file_too_large_title: `ファイルが大きすぎます`,
          file_too_large_description: `アップロードするファイルは {max_size} MB 以下である必要があります。`,
          download_failed_title: `ダウンロード失敗`,
          download_failed_description: `アップロードされたファイルをダウンロードできませんでした。もう一度お試しください。`,
          invalid_json_title: `無効なJSON`,
          invalid_json_description: `アップロードされたファイルは有効なJSONではありません。`,
          invalid_schema_title: `無効なLogit Bias形式`,
          invalid_schema_description: `\`text\` と \`value\` を持つSillyTavern形式の項目、またはその配列が必要です。Biasは {min} から {max}、text は最大 {max_length} 文字までです。`,
          no_entries_title: `項目が見つかりません`,
          no_entries_description: `アップロードされたファイルには有効なlogit bias項目がありませんでした。`,
          already_set_title: `変更はありません`,
          already_set_description: `アップロードされた項目はすべて、同じbias値で既に保存されています。`,
          success_title: `Logit Biasをインポートしました`,
          success_description: `新規 **{added_count}** 件を追加し、既存 **{updated_count}** 件を更新しました。\n保存合計: **{total_count}** 件\n現在のモデルで実行時に使える項目: **{runtime_ready_count}** 件`,
        },
      },
      timezone: {
        description: `サーバーのUTCオフセットを設定します（デフォルト: 0 / UTC）。`,
        value_description: `UTCオフセット（時間、デフォルト: 0）。例: 8、-5、0、9`,
        invalid_value_title: `無効なタイムゾーンオフセット`,
        invalid_value_description: `タイムゾーンオフセットは {min} から {max} 時間の間でなければなりません。`,
        already_set_title: `タイムゾーンは既に設定済みです`,
        already_set_description: `タイムゾーンは既に \`{timezone}\` に設定されています。`,
        success_title: `タイムゾーンが更新されました`,
        success_description: `サーバーのタイムゾーンが \`{previous_timezone}\` から \`{timezone}\` に変更されました。`,
      },
      permissions: {
        description: `このサーバーでの私のコアな行動権限を設定します。`,
        option_description: `設定する特定の権限。`,
        selfteaching_option: `自己学習`,
        personalization_option: `パーソナライズ (記憶/ニックネーム)`,
        emojiusage_option: `絵文字の使用`,
        stickerusage_option: `スタンプの使用`,
        websearch_option: "ウェブ検索権限",
        pinmessage_option: "メッセージのピン留め",
        imagegen_option: "画像生成",
        hiderespondembed_option: "応答埋め込みを非表示",
        hideimpersonationembeds_option: "なりすまし埋め込みを非表示",
        voicemessage_option: "ボイスメッセージ（ElevenLabs）",
        permission_choice_selfteaching: `自己学習`,
        permission_choice_personalization: `パーソナライズ (記憶/ニックネーム)`,
        permission_choice_emojiusage: `絵文字の使用`,
        permission_choice_stickerusage: `スタンプの使用`,
        permission_choice_websearch: "ウェブ検索権限",
        permission_choice_pinmessage: "メッセージのピン留め",
        permission_choice_imagegen: "画像生成",
        permission_choice_hiderespondembed: "応答埋め込みを非表示",
        // セレクトメニューに表示する短い説明文
        selfteaching_desc: "サーバーの会話から学習する",
        personalization_desc: "個人記憶とニックネーム",
        emojiusage_desc: "返答に絵文字を使用する",
        stickerusage_desc: "スタンプを送信する",
        websearch_desc: "ウェブで情報を検索する",
        pinmessage_desc: "重要なメッセージをピン留め",
        imagegen_desc: "リクエストに応じて画像生成",
        hiderespondembed_desc: "/bot respond の成功埋め込みを非表示",
        hideimpersonationembeds_desc: "なりすまし通知を非表示",
        voicemessage_desc: "ElevenLabs TTSボイスメッセージを送信",
        // チェックボックスセレクトメニューの文字列
        select_placeholder: "有効にする権限を選択...",
        select_embed_title: "権限の設定",
        select_embed_description: "**有効にする**権限を選択してください。チェックあり = 有効、チェックなし = 無効。",
        no_changes_title: "変更なし",
        no_changes_description: "すべての権限はすでに選択した値に設定されています。",
        timed_out_title: "タイムアウト",
        timed_out_description: "権限メニューがタイムアウトしました。変更は適用されませんでした。",
        set_description: `私のためにこの権限を有効または無効にします。`,
        already_set_title: `権限は既に設定済みです`,
        already_enabled_description: `権限 \`{permission_type}\` は既に**有効**です。`,
        already_disabled_description: `権限 \`{permission_type}\` は既に**無効**です。`,
        success_title: `権限が更新されました`,
        success_description: `**{count}** 件の権限を更新しました。`,
        enabled_success: `\`{permission_type}\` の権限が**有効**になりました。`,
        disabled_success: `\`{permission_type}\` の権限が**無効**になりました。`,
      },
      uncensors: {
        description: `このサーバーでのプロンプト向けの任意のuncensor機能を設定します。`,
        option_description: `設定するuncensor項目。`,
        injection_option: `プロンプト注入（18+同意の確認）`,
        unicode_spaces_option: `Unicodeスペース置換`,
        sanitize_option: `センシティブ語句のサニタイズ`,
        set_description: `このuncensor項目を有効または無効にします。`,
        already_set_title: `Uncensor項目は既に設定済みです`,
        already_enabled_description: `uncensor項目 \`{uncensor_type}\` は既に**有効**です。`,
        already_disabled_description: `uncensor項目 \`{uncensor_type}\` は既に**無効**です。`,
        success_title: `Uncensor項目が更新されました`,
        enabled_success: `uncensor項目 \`{uncensor_type}\` が**有効**になりました。`,
        disabled_success: `uncensor項目 \`{uncensor_type}\` が**無効**になりました。`,
        injection_ack_notice: `注意：有効化すると、サーバーの全メンバーが法定年齢であることに同意したものとみなされます。`,
      },

      // システムプロンプト管理
      sysprompt: {
        description: `人格指示のためのカスタムシステムプロンプトを管理します`,
        change: {
          description: `私の振る舞いを導くカスタムシステムプロンプトを設定します`,
        },
        clear: {
          description: `カスタムシステムプロンプトを削除し、デフォルトのシステムプロンプトを使用します`,
        },
        preset: {
          description: `プリセットシステムプロンプトを適用します`,
        },
      },
      prompt: {
        description: `人格指示のためのカスタムシステムプロンプトを管理します`,
        change: {
          description: `私の振る舞いを導くカスタムシステムプロンプトを設定します`,
          modal_title: `カスタムシステムプロンプトを設定`,
          part1_label: `システムプロンプト（1/4）`,
          part1_description: `主な指示。{bot} は私の名前、{user} はトリガーしたユーザーとして使用できます`,
          part1_placeholder: `例：{bot} はフレンドリーで親切...`,
          part2_label: `システムプロンプト（2/4）- 任意`,
          part2_description: `指示の続き（任意）`,
          part2_placeholder: `追加の指示...`,
          part3_label: `システムプロンプト（3/4）- 任意`,
          part3_description: `指示の続き（任意）`,
          part3_placeholder: `さらに指示...`,
          part4_label: `システムプロンプト（4/4）- 任意`,
          part4_description: `指示の続き（任意）`,
          part4_placeholder: `最後の指示...`,
          empty_prompt_title: `空のシステムプロンプト`,
          empty_prompt_description: `システムプロンプトは空にできません。少なくともパート1に指示を入力してください。`,
          success_title: `システムプロンプトが更新されました`,
          success_description: `カスタムシステムプロンプトを設定しました：\n\`\`\`\n{preview}...\n\`\`\``,
        },
        clear: {
          description: `カスタムシステムプロンプトを削除し、デフォルトのシステムプロンプトを使用します`,
          no_custom_prompt_title: `カスタムプロンプトは未設定です`,
          no_custom_prompt_description: `カスタムシステムプロンプトは設定されていません。現在はデフォルトのプロンプトを使用しています：\n\`\`\`\n{defaultPrompt}\n\`\`\``,
          success_title: `システムプロンプトがクリアされました`,
          success_description: `カスタムシステムプロンプトをクリアしました。現在はデフォルトのプロンプトを使用します：\n\`\`\`\n{defaultPrompt}\n\`\`\``,
        },
        preset: {
          description: `プリセットシステムプロンプトを適用します`,
          modal_title: `システムプロンプトプリセットを選択`,
          selection_label: `プリセットを選択`,
          selection_placeholder: `プリセットのプロンプトスタイルを選択...`,
          success_title: `✓ プリセットが適用されました`,
          success_description: `システムプロンプトプリセットを適用しました：**{presetName}**\nプレビュー：\n\`\`\`\n{preview}...\n\`\`\``,
          no_presets_title: `プリセットがありません`,
          no_presets_description: `システムプロンプトプリセットが見つかりません。ボット管理者にお問い合わせください。`,
          invalid_preset_title: `無効なプリセット`,
          invalid_preset_description: `選択されたプリセットが見つかりませんでした。もう一度お試しください。`,
        },
      },

      // ランダムトリガー管理（タイマーベースの確率的自動トリガー）
      randomtrigger: {
        add: {
          description: `チャンネルに確率的なタイマーベースの自動トリガーを追加します。`,
          channel_description: `自発的なメッセージを送信するチャンネル。`,
          timer_hours_description: `サイコロを振る頻度（時間単位、最低1時間）。`,
          random_offset_range_description: `タイマーがリセットされるたびに加算/減算するランダムオフセット範囲（時間、任意、最小0）。`,
          chance_description: `各ロールで発火する確率（1〜100%）。`,
          silence_threshold_description: `このX時間以内にチャンネルに活動があった場合はスキップ（任意）。`,
          failure_threshold_description: `連続してサイコロを外れた回数がこの値に達したら強制発火し、カウンターをリセットします（任意）。`,
          modal_title: `ランダムトリガーの設定`,
          persona_select_label: `ペルソナ`,
          persona_select_description: `発言するペルソナ。「ランダム」は毎回1つを選択します。`,
          persona_select_placeholder: `ペルソナを選択...`,
          persona_random_label: `ランダム（毎回選択）`,
          respond_to_self_label: `自分への返答`,
          respond_to_self_description: `このペルソナが最後に発言した場合でも発火しますか？`,
          respond_to_self_yes: `はい`,
          respond_to_self_no: `いいえ`,
          prompt_label: `カスタムプロンプト（任意）`,
          prompt_description: `このトリガーのメッセージに注入される追加指示。`,
          prompt_placeholder: `例：天気について話題を始めて...`,
          cap_reached_title: `トリガー上限に達しました`,
          cap_reached_description: `このサーバーはランダムトリガーの最大数{max}に達しました。先に1つ削除してください。`,
          override_title: `トリガーが更新されました`,
          override_description: `{channel}の{persona}のトリガーが既に存在していたため、新しい設定で更新されました。`,
          success_title: `ランダムトリガーを追加しました`,
          success_description: `{channel}を**{timer_hours}時間**ごとに確認し、**{chance}%**の確率で**{persona}**として発言します。{offset_suffix}{silence_suffix}{failure_suffix}`,
          success_offset_suffix: ` リセットごとに最大**+/-{random_offset_range}時間**のランダムオフセットを加算/減算します。`,
          success_silence_suffix: ` **{silence_threshold}時間**以内に活動があった場合はスキップします。`,
          success_failure_suffix: ` **{failure_threshold}**回連続でミスした場合に強制発火します。`,
        },
        remove: {
          description: `このサーバーからランダムトリガーを削除します。`,
          modal_title: `ランダムトリガーの削除`,
          checkbox_label: `ランダムトリガー`,
          checkbox_label_continued: `ランダムトリガー（続き）`,
          checkbox_description: `削除したいランダムトリガーのチェックを外してください。`,
          select_label: `削除するトリガー`,
          select_description: `削除するランダムトリガーを選択します。`,
          select_placeholder: `トリガーを選択...`,
          none_title: `トリガーが見つかりません`,
          none_description: `このサーバーにはランダムトリガーが設定されていません。`,
          no_removals_title: `削除されたランダムトリガーはありません`,
          no_removals_description: `どのランダムトリガーも未チェックになっていません。変更は行われていません。`,
          success_title: `ランダムトリガーを更新しました`,
          success_description: `次のランダムトリガーを削除しました。\n{triggers_removed}`,
        },
      },

      // モデル上書き削除（サブコマンドグループ）
      remove: {
        description: `サーバー設定から上書きとフォールバックを削除します。`,
        modeloverride: {
          description: `チャンネルとペルソナのモデル上書きを削除します。`,
          modal_title: `モデル上書きの削除`,
          channel_checkbox_label: `チャンネル上書き`,
          channel_checkbox_label_continued: `チャンネル上書き（続き）`,
          channel_checkbox_description: `削除したいチャンネル上書きのチェックを外してください。`,
          persona_checkbox_label: `ペルソナ上書き`,
          persona_checkbox_label_continued: `ペルソナ上書き（続き）`,
          persona_checkbox_description: `削除したいペルソナ上書きのチェックを外してください。`,
          none_title: `モデル上書きなし`,
          none_description: `このサーバーにはチャンネルまたはペルソナのモデル上書きが設定されていません。`,
          too_many_title: `モデル上書きが多すぎます`,
          too_many_description: `このサーバーにはチャンネル上書きが **{channel_count}** 件、ペルソナ上書きが **{persona_count}** 件（合計 **{total_count}** 件）あります。Discord のモーダルではチェックボックスグループを **{max_groups}** 個（合計 **{max_entries}** 項目）までしか表示できません。`,
          no_removals_title: `削除されたモデル上書きはありません`,
          no_removals_description: `どの上書きも未チェックになっていません。モデル上書きは変更されていません。`,
          success_title: `モデル上書きを更新しました`,
          success_description: `次のモデル上書きを削除しました。\n{removed_overrides}`,
        },
        modelfallback: {
          description: `フォールバックチェーンからモデルを削除します。`,
          modal_title: `フォールバックモデルの削除`,
          checkbox_label: `フォールバックモデル`,
          checkbox_description: `削除したいフォールバックモデルのチェックを外してください。チェックしたモデルは現在の順序のまま残ります。`,
          none_title: `フォールバック未設定`,
          none_description: `このサーバーにはフォールバックモデルが設定されていません。`,
          no_removals_title: `削除されたフォールバックモデルはありません`,
          no_removals_description: `どのフォールバックモデルも未チェックになっていません。フォールバックチェーンは変更されていません。`,
          success_title: `フォールバックチェーンを更新しました`,
          success_description: `次のフォールバックモデルを削除しました: {models_removed}\n残り{remaining_count}件。`,
        },
      },
      mcp: {
        description: `リモートMCP（Model Context Protocol）ツールサーバーを管理`,
        add: {
          description: `このギルドに新しいリモートMCPサーバーを登録します。/help mcp でセットアップガイドを確認できます。`,
          modal_title: `MCPサーバーを追加`,
          name_label: `サーバー名`,
          name_placeholder: `my-mcp-server`,
          url_label: `サーバーURL`,
          url_placeholder: `https://mcp.example.com/sse`,
          auth_token_label: `認証トークン（任意）`,
          auth_token_placeholder: `BearerトークンまたはSmithery APIキー（不要な場合は空白）`,
          server_type_label: `サーバータイプ（任意）`,
          server_type_description: `このサーバーが置き換える機能（対応する内蔵ツールを無効化）`,
          server_type_placeholder: `サーバータイプを選択...`,
          none_option: `汎用`,
          none_option_description: `内蔵ツールは無効化されません`,
          web_search_option: `ウェブ検索`,
          web_search_option_description: `内蔵のBraveおよびDuckDuckGo検索ツールを無効化`,
          url_fetcher_option: `URL取得`,
          url_fetcher_option_description: `内蔵のURL取得ツールを無効化`,
          invalid_input_title: `入力不足`,
          invalid_input_description: `サーバー名とURLの両方が必要です。`,
          invalid_name_title: `無効なサーバー名`,
          invalid_name_description: `サーバー名は英数字とハイフンのみ使用可能（1〜32文字）で、英数字で始まる必要があります。`,
          invalid_url_title: `無効なURL`,
          invalid_url_invalid_format_description: `MCPサーバーURLの形式が正しくありません。`,
          invalid_url_protocol_description: `MCPサーバーURLはHTTPまたはHTTPSを使用する必要があります。`,
          invalid_url_http_localhost_only_description: `開発環境では、HTTPはlocalhostのMCPサーバーにのみ使用できます。リモートサーバーにはHTTPSを使ってください。`,
          invalid_url_https_required_description: `本番環境ではTLS付きのHTTPS MCPサーバーのみ許可されています。`,
          invalid_url_localhost_blocked_description: `本番環境ではlocalhostのMCPサーバーは使用できません。`,
          invalid_url_dns_failed_description: `ホスト名 \`{hostname}\` をこのサーバーから解決できませんでした。`,
          invalid_url_private_address_description: `本番環境では公開ルーティング可能なMCPホストのみ許可されています。このホスト名はブロック対象アドレス \`{address}\` に解決されました。`,
          limit_reached_title: `サーバー上限に達しました`,
          limit_reached_description: `このギルドはMCPサーバーの上限（{max}台）に達しています。新しいサーバーを追加する前に既存のサーバーを削除してください。`,
          connection_failed_title: `接続失敗`,
          connection_failed_description: `MCPサーバーに接続できませんでした。\n**エラー:** {error}`,
          duplicate_name_title: `名前が重複`,
          duplicate_name_description: `"{name}"という名前のMCPサーバーはこのギルドに既に存在します。`,
          success_title: `MCPサーバーを追加しました`,
          success_description: `**{name}**の登録に成功しました。\n**URL:** \`{url}\`\n**発見されたツール:** {tool_count}件 ({tool_names})\n\n信頼できるMCPサーバーだけを追加してください。\n悪意のあるサーバーは、まぎらわしい指示を返したり、ツールに送られた情報を集めたり、危険または誤った結果を返すおそれがあります。`,
        },
        remove: {
          description: `このギルドから登録済みのMCPサーバーを削除します。`,
          modal_title: `MCPサーバーを削除`,
          checkbox_label: `登録済みMCPサーバー`,
          checkbox_label_continued: `登録済みMCPサーバー（続き）`,
          checkbox_description: `削除したいMCPサーバーのチェックを外してください。`,
          too_many_title: `MCPサーバーが多すぎます`,
          too_many_description: `このギルドには登録済みMCPサーバーが **{count}** 台あります。Discord のモーダルではチェックボックスグループを **{max_groups}** 個（合計 **{max_entries}** 項目）までしか表示できません。`,
          no_removals_title: `削除されたMCPサーバーはありません`,
          no_removals_description: `どのMCPサーバーも未チェックになっていません。登録済みサーバーは変更されていません。`,
          not_found_title: `サーバーが見つかりません`,
          not_found_description: `"{name}"という名前のMCPサーバーはこのギルドに見つかりませんでした。`,
          success_title: `MCPサーバーを更新しました`,
          success_description: `次のMCPサーバーを削除して切断しました。\n{servers_removed}`,
        },
        list: {
          description: `このギルドの登録済みMCPサーバーを一覧表示します。`,
          empty_title: `MCPサーバーなし`,
          empty_description: `このギルドにはMCPサーバーが登録されていません。\`/config mcp add\`で登録してください。`,
          title: `登録済みMCPサーバー`,
          header_description: `**{count}**台のサーバーが登録済み:\n\n{servers}`,
        },
        toggle: {
          description: `登録済みMCPサーバーの有効/無効を切り替えます。`,
          modal_title: `MCPサーバーの切り替え`,
          select_label: `サーバーを選択`,
          select_description: `切り替えるMCPサーバーを選択してください`,
          select_placeholder: `切り替えるサーバーを選択...`,
          state_label: `有効/無効`,
          state_description: `サーバーを有効にするか無効にするかを選択`,
          state_placeholder: `状態を選択...`,
          currently_enabled: `有効`,
          currently_disabled: `無効`,
          enable_option: `有効にする`,
          enable_option_description: `このMCPサーバーをツール呼び出しに有効化`,
          disable_option: `無効にする`,
          disable_option_description: `このMCPサーバーを無効化して切断`,
          not_found_title: `サーバーが見つかりません`,
          not_found_description: `"{name}"という名前のMCPサーバーはこのギルドに見つかりませんでした。`,
          enabled_success_title: `MCPサーバーを有効化しました`,
          enabled_success_description: `MCPサーバー"{name}"が有効化され、ツール呼び出しに使用可能になりました。`,
          disabled_success_title: `MCPサーバーを無効化しました`,
          disabled_success_description: `MCPサーバー"{name}"が無効化され、切断されました。`,
        },
      },
    },

    optionalkey: {
      description: `オプションのサービスAPIキーを管理`,
      brave: {
        description: `Brave Search APIキーを管理`,
        set: {
          description: `このサーバーのBrave Search APIキーを設定します。`,
          key_description: `あなたのBrave Search APIキー。`,
          invalid_key_title: `無効なAPIキー形式`,
          invalid_key_description: `提供されたAPIキーは短すぎるか無効のようです。有効なキーを提供してください。`,
          validating_key: `Brave Search APIキーを検証中...`,
          validation_error_title: `APIキーの検証エラー`,
          validation_error_description: `Brave Search APIキーの検証中にエラーが発生しました。再度お試しいただくか、接続を確認してください。`,
          key_validation_failed_title: `Brave APIキーの検証に失敗しました`,
          key_validation_failed_description: `提供されたBrave Search APIキーは無効です。キーを確認してもう一度お試しください。`,
          success_title: `Brave APIキーが設定されました`,
          success_description: `Brave Search APIキーが正常に検証、暗号化、保存されました。`,
        },
        remove: {
          description: `現在設定されているBrave Search APIキーを削除します。`,
          no_key_title: `Brave APIキーが設定されていません`,
          no_key_description: `現在削除するBrave Search APIキーが設定されていません。`,
          success_title: `Brave APIキーが削除されました`,
          success_description: `Brave Search APIキーが正常に削除されました。`,
        },
      },
      google: {
        description: `補助Google APIキーを管理（画像インペインティング用）`,
        set: {
          description: `画像セグメンテーション用Google APIキー。Googleがメインプロバイダーの場合は不要。`,
          key_description: `あなたのGoogle APIキー。`,
          invalid_key_title: `無効なAPIキー形式`,
          invalid_key_description: `提供されたAPIキーは短すぎるか無効のようです。有効なGoogle APIキーを提供してください。`,
          key_validation_failed_title: `Google APIキーの検証に失敗しました`,
          key_validation_failed_description: `提供されたGoogle APIキーは無効です。キーを確認してもう一度お試しください。`,
          success_title: `Google APIキーが設定されました`,
          success_description: `Google APIキーが正常に検証、暗号化、保存されました。AIの画像セグメンテーション（インペインティング）に使用されます。メインプロバイダーがすでにGoogleの場合、このキーがセグメンテーションで優先されます。`,
        },
        remove: {
          description: `現在設定されているGoogle APIキーを削除します。`,
          no_key_title: `Google APIキーが設定されていません`,
          no_key_description: `現在削除するGoogle APIキーが設定されていません。`,
          success_title: `Google APIキーが削除されました`,
          success_description: `Google APIキーが正常に削除されました。`,
        },
      },
      novelai: {
        description: `補助NovelAI APIキーを管理（画像生成用）`,
        set: {
          description: `画像生成用NovelAI APIキー。NovelAIがメインプロバイダーの場合は不要。`,
          key_description: `あなたのNovelAI APIキー。`,
          disable_other_imggen_description: `trueの場合、標準の画像生成ツールを非表示にし、NovelAI画像生成のみを利用可能にします。`,
          invalid_key_title: `無効なAPIキー形式`,
          invalid_key_description: `提供されたAPIキーは短すぎるか無効のようです。有効なNovelAI APIキーを提供してください。`,
          key_validation_failed_title: `NovelAI APIキーの検証に失敗しました`,
          key_validation_failed_description: `提供されたNovelAI APIキーは無効です。キーを確認し、有効なサブスクリプションがあることを確認してください。`,
          success_title: `NovelAI APIキーが設定されました`,
          success_description: `NovelAI APIキーが正常に検証、暗号化、保存されました。アクティブなLLMプロバイダーに関係なく、NovelAI画像生成が利用可能になりました。`,
          success_exclusive_description: `NovelAI APIキーが正常に検証、暗号化、保存されました。NovelAI画像生成がこのサーバーの唯一の画像生成ツールになりました。`,
        },
        remove: {
          description: `現在設定されているNovelAI APIキーを削除します。`,
          no_key_title: `NovelAI APIキーが設定されていません`,
          no_key_description: `現在削除するNovelAI APIキーが設定されていません。`,
          success_title: `NovelAI APIキーが削除されました`,
          success_description: `NovelAI APIキーと排他的画像生成設定が削除されました。`,
        },
      },
      elevenlabs: {
        description: `補助ElevenLabs APIキーを管理（音声認識・音声出力用）`,
        set: {
          description: `音声文字起こしとペルソナの音声出力に使うElevenLabs APIキーを設定します。`,
          key_description: `あなたのElevenLabs APIキー。`,
          invalid_key_title: `無効なAPIキー形式`,
          invalid_key_description: `提供されたAPIキーは短すぎるか無効のようです。有効なElevenLabs APIキーを入力してください。`,
          key_validation_failed_title: `ElevenLabs APIキーの検証に失敗しました`,
          key_validation_failed_description: `提供されたElevenLabs APIキーは無効です。キーを確認してもう一度お試しください。`,
          success_title: `ElevenLabs APIキーが設定されました`,
          success_description: `ElevenLabs APIキーが正常に検証、暗号化、保存されました。設定されている場所では音声文字起こしとペルソナの音声出力が利用可能になります。`,
          success_voices_title: `プリメイド音声（無料プラン対応）`,
          success_voices_description: `プリメイド音声は無料プランでも利用できます。一覧は [ElevenLabs Premade Voices](https://elevenlabs-sdk.mintlify.app/voices/premade-voices) で確認し、{configVoiceElevenlabs} で各ペルソナに割り当てましょう。`,
          success_custom_voices_title: `ライブラリ音声・カスタム音声（有料プラン必須）`,
          success_custom_voices_description: `ライブラリ音声とカスタム（クローン・生成）音声はどちらもElevenLabsの有料プランが必要です。アカウントに追加した音声は {configVoiceElevenlabs} に自動で表示されます。`,
          success_transcript_mode_title: `音声トランスクリプトモード`,
          success_transcript_mode_description: `{configVoiceTranscripts} を使うと、音声メッセージのトランスクリプトをWebhook経由でチャットメッセージとして投稿できます。再処理クレジットの節約と透明性の向上に役立ちます。`,
        },
        remove: {
          description: `現在設定されているElevenLabs APIキーを削除します。`,
          no_key_title: `ElevenLabs APIキーが設定されていません`,
          no_key_description: `現在削除するElevenLabs APIキーは設定されていません。`,
          success_title: `ElevenLabs APIキーが削除されました`,
          success_description: `ElevenLabs APIキーが正常に削除されました。`,
        },
      },
    },

    // サーバー設定コマンド（管理者専用）
    server: {
      // RPチャンネル管理（サブコマンドグループ）
      rpchannel: {
        description: `絵文字とスタンプを常に非表示にするRPチャンネルを管理`,
        add: {
          description: `RPチャンネルリストにチャンネルを追加します（絵文字とスタンプを無効化）。`,
          channel_description: `RPチャンネルリストに追加するテキストチャンネル。`,
          success_title: `RPチャンネルが追加されました`,
          success_description: `\`{channel_name}\` をRPチャンネルリストに正常に追加しました。そのチャンネルでは絵文字とスタンプが常に非表示になります。`,
          already_added_title: `チャンネルは既にリストにあります`,
          already_added_description: `チャンネル \`{channel_name}\` は既にRPチャンネルリストにあります。`,
        },
        remove: {
          description: `RPチャンネルリストからチャンネルを削除します。`,
          channel_description: `RPチャンネルリストから削除するテキストチャンネル。`,
          success_title: `RPチャンネルが削除されました`,
          success_description: `\`{channel_name}\` をRPチャンネルリストから正常に削除しました。そのチャンネルでは絵文字とスタンプがグローバル設定に従います。`,
          not_found_title: `チャンネルが見つかりません`,
          not_found_description: `チャンネル \`{channel_name}\` はRPチャンネルリストにありません。`,
        },
      },
      // 自動チャット設定（サブコマンドグループ）
      autotrigger: {
        description: `自動チャット設定を管理`,
        channels: {
          description: `私が自動的にチャットするチャンネルを追加または削除します。`,
          channel_description: `追加または削除するテキストチャンネル。`,
          action_description: `チャンネルを追加するか削除するか。`,
          invalid_channel_title: `無効なチャンネルタイプ`,
          invalid_channel_description: `標準のテキストチャンネルを選択してください。`,
          already_added_title: `チャンネルは既に追加されています`,
          already_added_description: `チャンネル \`{channel_name}\` は既に自動チャットリストにあります。`,
          not_in_list_title: `チャンネルが見つかりません`,
          not_in_list_description: `チャンネル \`{channel_name}\` は自動チャットリストにありません。`,
          added_title: `自動チャットチャンネルが追加されました`,
          added_description: `\`{channel_name}\` を自動チャットチャンネルに正常に追加しました。`,
          removed_title: `自動チャットチャンネルが削除されました`,
          removed_description: `\`{channel_name}\` を自動チャットチャンネルから正常に削除しました。`,
        },
        threshold: {
          description: `設定済みの自動チャットチャンネル用の共有自動チャット範囲を設定します。`,
          threshold_description: `自動チャットまでの最小メッセージ数。0 で常時応答モードになります。`,
          max_description: `自動チャットまでの任意の最大メッセージ数。空欄なら最小値と同じになります。`,
          invalid_range_title: `無効な閾値`,
          invalid_range_specific_description: `常時応答モードには \`{always}\` を使用してください。それ以外は、両方の値を \`{min}\` から \`{max}\` の間にし、最大値を最小値以上にしてください。`,
          success_title: `自動チャット閾値が設定されました`,
          success_description: `指定されたチャンネルで \`{threshold}\` メッセージ後に自動的にチャットします。`,
          success_range_title: `自動チャット範囲が設定されました`,
          success_range_description: `指定されたチャンネルで、\`{min}\` から \`{max}\` メッセージのランダムな間隔で自動的にチャットします。`,
          success_always_title: `自動チャット常時応答モードを設定しました`,
          success_always_description: `自動チャットの閾値を \`{threshold}\` に設定しました。設定済みの自動チャットチャンネルでは、対象メッセージに対して常時応答のように動作します。無効化したい場合はそのチャンネルをリストから削除してください。`,
        },
      },
      // トリガーワード管理（サブコマンドグループ）
      trigger: {
        description: `トリガーワードを管理`,
        add: {
          description: `ペルソナのトリガーワードを追加します。`,
          word_description: `トリガーとして追加する単語。`,
          modal_title: `トリガーワードを追加`,
          persona_select_label: `ペルソナ`,
          persona_select_description: `追加先のペルソナを選択してください。`,
          persona_select_placeholder: `ペルソナを選択...`,
          triggers_input_label: `トリガーワード`,
          triggers_input_description: `カンマ区切りで入力してください（"," または "、"）。`,
          triggers_input_placeholder: `例: ともり, トモリ`,
          main_persona_description: `メインペルソナ`,
          alter_persona_description: `オルタペルソナ`,
          no_triggers_title: `トリガーワードがありません`,
          no_triggers_description: `少なくとも1つのトリガーワードを入力してください。`,
          too_short_title: `トリガーワードが短すぎます`,
          too_short_description: `トリガーワードは少なくとも2文字以上である必要があります。`,
          content_too_long_title: `トリガーワードが長すぎます`,
          content_too_long_description: `トリガーワードは {max_length} 文字を超えることはできません。`,
          already_exists_title: `トリガーワードが存在します`,
          already_exists_description: `単語 \`{word}\` は既にトリガーリストにあります。`,
          already_exists_multiple_description: `これらのトリガーワードは既に存在します: {words}。`,
          limit_exceeded_title: `トリガーワード上限に達しました`,
          limit_exceeded_description: `このサーバーはトリガーワードを最大 {max_allowed} 個まで設定できます（現在 {current_count} 個）。新しいものを追加する前に、\`/server trigger delete\`でいくつかのトリガーワードを削除してください。`,
          success_title: `トリガーワードが追加されました`,
          success_description: `{persona_name} に {added_count} 個のトリガーワードを追加しました: {added_words}。現在 {word_count} 個のトリガーワードがあります。`,
        },
        delete: {
          description: `言及されたときに私が応答する単語を削除します。`,
          no_triggers_title: `トリガーワードがありません`,
          no_triggers_description: `削除するカスタムトリガーワードが設定されていません。\`/server trigger add\`で追加してください。`,
          select_title: `トリガーワードの削除`,
          select_description: `削除したいトリガーワードを選択してください`,
          trigger_words_label: `トリガーワード`,
          modal_title: `トリガーワードの削除`,
          checkbox_label: `トリガーワード`,
          checkbox_label_continued: `トリガーワード（続き）`,
          checkbox_description: `削除したいトリガーワードのチェックを外してください。`,
          select_label: `トリガーワード`,
          select_placeholder: `削除するトリガーワードを選択してください`,
          no_removals_title: `削除されたトリガーワードはありません`,
          no_removals_description: `どのトリガーワードも未チェックになっていません。変更は行われていません。`,
          success_title: `トリガーワードを更新しました`,
          success_description: `次のトリガーワードを削除しました: {triggerWords}`,
        },
      },
      blacklist: {
        description: `パーソナライズのブラックリストにメンバーを追加または削除します。`,
        member_description: `ブラックリストに追加または削除するメンバー。`,
        action_description: `メンバーを追加するか削除するか。`,
        personalization_disabled_title: `パーソナライズが無効です`,
        personalization_disabled_description: `現在、サーバー全体でパーソナライズが無効になっています。まず \`/config permissions\` で有効にしてください。`,
        already_blacklisted_title: `既にブラックリストに登録されています`,
        already_blacklisted_description: `\`{user_name}\` は既にパーソナライズのブラックリストに登録されています。`,
        not_blacklisted_title: `ブラックリストに登録されていません`,
        not_blacklisted_description: `\`{user_name}\` はパーソナライズのブラックリストに登録されていません。`,
        added_title: `メンバーがブラックリストに登録されました`,
        added_description: `\`{user_name}\` をパーソナライズのブラックリストに追加しました。彼らの個人的な記憶とニックネームは使用されません。`,
        removed_title: `メンバーがブラックリストから解除されました`,
        removed_description: `\`{user_name}\` をパーソナライズのブラックリストから削除しました。彼らの個人的な記憶とニックネームが使用できるようになります。`,
        user_registration_failed_title: `ユーザー登録に失敗しました`,
        user_registration_failed_description: `データベースへのユーザー登録に失敗しました。もう一度お試しください。`,
        cannot_blacklist_bot_title: `ボットをブラックリスト登録できません`,
        cannot_blacklist_bot_description: `\`{user_name}\` はボットであり、パーソナライズのブラックリストに追加できません。`,
      },
      welcomechannel: {
        description: `新規参加メンバー向けの歓迎チャンネルを設定します。`,
        channel_description: `新規メンバーを歓迎するテキストチャンネル。`,
        action_description: `歓迎チャンネルを追加するか削除するか。`,
        modal_title: `歓迎メッセージを設定`,
        persona_select_label: `歓迎ペルソナ`,
        persona_select_description: `新規メンバーを歓迎するペルソナを選択します。ランダムは参加ごとに選びます。`,
        persona_select_placeholder: `ペルソナを選択...`,
        persona_random_label: `ランダム（参加ごとに選択）`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        prompt_label: `追加プロンプト`,
        prompt_description: `新しいユーザーをどのように歓迎しますか？`,
        prompt_placeholder: `Greet users by...`,
        empty_prompt_title: `追加プロンプトが必要です`,
        empty_prompt_description: `新しいユーザーをどのように歓迎するか入力してください。`,
        added_title: `歓迎チャンネルを更新しました`,
        added_description: `今後、新規メンバーを {channel} で **{persona}** として歓迎します。`,
        removed_title: `歓迎チャンネルを削除しました`,
        removed_description: `新規メンバー向けの自動歓迎メッセージは送信しなくなります。`,
        not_configured_title: `歓迎チャンネルは未設定です`,
        not_configured_description: `このサーバーには現在歓迎チャンネルが設定されていません。`,
      },
      thoughtlogs: {
        description: `このサーバーの思考ログチャンネルを設定または解除します。`,
        channel_description: `推論サマリーを投稿するテキストチャンネルです。同じチャンネルをもう一度選ぶと無効化されます。`,
        invalid_channel_title: `無効なチャンネル`,
        invalid_channel_description: `サーバーのテキストチャンネルを選択してください。`,
        set_title: `思考ログを有効化しました`,
        set_description: `今後、思考ログは {channel} に投稿されます。`,
        updated_title: `思考ログを更新しました`,
        updated_description: `今後、思考ログは {channel} に投稿されます。`,
        cleared_title: `思考ログを無効化しました`,
        cleared_description: `今後、思考ログは投稿されません。`,
      },
      whitelist: {
        description: `トリガーホワイトリストを管理（チャンネル＋ロール、チャンネル設定はグローバルクールダウンを上書き）`,
        channel: {
          description: `チャンネルをホワイトリストに追加し、必要ならグローバルクールダウンを上書き`,
          channel_description: `ホワイトリストに追加するチャンネル`,
          type_description: `任意の上書き: このチャンネルのクールダウンタイプ`,
          length_description: `任意の上書き: クールダウンの長さ（秒）（0 = 即座、クールダウンなし）`,
          invalid_channel_title: `無効なチャンネルタイプ`,
          invalid_channel_description: `テキストチャンネルのみをホワイトリストに追加できます。`,
          already_set_title: `既に設定されています`,
          already_set_description: `チャンネル **{channel_name}** には既にこれらの正確なホワイトリスト設定があります。`,
          invalid_type_title: `無効なクールダウンタイプ`,
          invalid_type_description: `選択されたクールダウンタイプは無効です。有効なオプションを選択してください。`,
          invalid_length_title: `無効なクールダウンの長さ`,
          invalid_length_description: `クールダウンの長さは **{min}** ～ **{max}** 秒の間である必要があります。`,
          success_inherit_title: `チャンネルがホワイトリストに登録されました`,
          success_inherit_description: `チャンネル **{channel_name}** をホワイトリストに登録し、このサーバーのグローバルクールダウンを継承するように設定しました。\n\n**注意:** いずれかのチャンネルがホワイトリストに登録されると、ホワイトリストに登録されたチャンネルのみがボットをトリガーできます。`,
          success_title: `チャンネルがホワイトリストに登録されました`,
          success_description: `チャンネル **{channel_name}** を、チャンネル固有の **{cooldown_type}** クールダウン（**{cooldown_length}** 秒）でホワイトリストに登録しました。\n\n**注意:** いずれかのチャンネルがホワイトリストに登録されると、ホワイトリストに登録されたチャンネルのみがボットをトリガーできます。`,
          success_instant_title: `チャンネルがホワイトリストに登録されました（即座）`,
          success_instant_description: `チャンネル **{channel_name}** を、チャンネル固有の **{cooldown_type}** 上書き（0秒 = 即座、クールダウンなし）でホワイトリストに登録しました。\n\n**注意:** いずれかのチャンネルがホワイトリストに登録されると、ホワイトリストに登録されたチャンネルのみがボットをトリガーできます。`,
        },
        role: {
          description: `ボットをトリガーできるロールホワイトリストを追加・削除`,
          role_description: `ホワイトリストに追加または削除するロール`,
          action_description: `このロールを追加するか削除するか選択`,
          action_add: `追加`,
          action_remove: `削除`,
          invalid_role_title: `無効なロール`,
          invalid_role_description: `@everyone ロールはロールホワイトリストに使用できません。`,
          already_set_title: `既に設定されています`,
          already_set_description: `ロール {role_mention} は既にホワイトリストに登録されています。`,
          not_set_title: `未設定`,
          not_set_description: `ロール {role_mention} はホワイトリストに登録されていません。`,
          success_add_title: `ロールがホワイトリストに登録されました`,
          success_add_description: `ロール {role_mention} は、ロールホワイトリストが有効なときにボットをトリガーできるようになりました。`,
          success_remove_title: `ロールがホワイトリストから削除されました`,
          success_remove_description: `ロール {role_mention} をホワイトリストから削除しました。`,
        },
        remove: {
          description: `ホワイトリストからチャンネルまたはロールを削除`,
          modal_title: `ホワイトリスト項目を削除`,
          checkbox_label: `ホワイトリスト中のチャンネル`,
          checkbox_label_continued: `ホワイトリスト中のチャンネル（続き）`,
          checkbox_description: `ホワイトリストから外したいチャンネルのチェックを外してください。`,
          role_checkbox_label: `ホワイトリスト中のロール`,
          role_checkbox_label_continued: `ホワイトリスト中のロール（続き）`,
          role_checkbox_description: `ホワイトリストから外したいロールのチェックを外してください。`,
          no_entries_title: `ホワイトリスト項目がありません`,
          no_entries_description: `削除するホワイトリスト中のチャンネルまたはロールがありません。`,
          too_many_entries_title: `ホワイトリスト項目が多すぎます`,
          too_many_entries_description: `このサーバーにはホワイトリスト中のチャンネルが **{channel_count}** 件、ロールが **{role_count}** 件あります。Discord のモーダルではチェックボックスグループを **{max_groups}** 個（合計 **{max_entries}** 項目）までしか表示できません。`,
          no_removals_title: `削除されたホワイトリスト項目はありません`,
          no_removals_description: `どのホワイトリスト項目も未チェックになっていません。変更は行われていません。`,
          success_title: `ホワイトリストを更新しました`,
          success_description: `次のホワイトリスト項目を削除しました。\n**チャンネル:** {channels_removed}\n**ロール:** {roles_removed}`,
        },
      },
      cooldown: {
        description: `クールダウンの管理`,
        triggers: {
          description: `トリガーと /bot のクールダウンを設定します（デフォルト: オフ、5秒）。`,
          cooldown_type_description: `クールダウン適用方法（デフォルト: オフ、ユーザーごと等）。`,
          cooldown_length_description: `クールダウン時間（秒、1-86400、デフォルト: 5）。`,
          invalid_type_title: `無効なクールダウンタイプ`,
          invalid_type_description: `選択されたクールダウンタイプが無効です。有効なオプションを選択してください。`,
          invalid_length_title: `無効な時間`,
          invalid_length_description: `時間は {min} から {max} 秒（24時間）の間で指定してください。`,
          already_set_title: `既に設定済み`,
          already_set_description: `クールダウン設定は既に **{type}**（**{length}** 秒）です。`,
          success_title: `クールダウンを更新しました`,
          success_description: `クールダウンを **{previous_type}**（**{previous_length}** 秒）から **{type}**（**{length}** 秒）に更新しました。これはメッセージトリガーと \`/bot\` コマンドの両方に適用されます。`,
          success_disabled_title: `クールダウンが無効化されました`,
          success_disabled_description: `クールダウンを **{previous_type}**（**{previous_length}** 秒）から **{type}**（**{length}** 秒）に更新しました。メッセージトリガーと \`/bot\` コマンドのクールダウンは現在 **無効** です。`,
          type: {
            choice_off: `オフ`,
            choice_per_user: `ユーザーごと`,
            choice_per_channel: `チャンネルごと`,
            choice_server_wide: `サーバー全体`,
            choice_strict_server_wide: `厳密サーバー全体`,
          },
        },
      },
      quota: {
        description: `生成クォータを管理`,
        imagegen: {
          description: `このサーバーの日次画像生成クォータを設定します。`,
          unlimited: `無制限`,
          daily_user_quota_description: `ユーザーごとの日次画像生成制限を設定します。`,
          daily_user_quota_limit_description: `ユーザー1人あたりの日次画像数（0=無制限、1-100、デフォルト: 10）。`,
          daily_user_quota_success_title: `ユーザークォータが更新されました`,
          daily_user_quota_success_description: `ユーザークォータが1日あたり **{limit}** 枚の画像に設定されました。`,
          serverwide_quota_description: `サーバー全体の画像生成制限の合計を設定します。`,
          serverwide_quota_limit_description: `サーバー全体の画像数（0=無制限、1-99999、デフォルト: 0）。`,
          serverwide_quota_success_title: `サーバー全体のクォータが更新されました`,
          serverwide_quota_success_description: `サーバー全体のクォータが期間あたり **{limit}** 枚の画像に設定されました。`,
          serverwide_quota_resets_in_description: `サーバー全体のクォータがリセットされるまでの日数を設定します。`,
          serverwide_quota_resets_in_days_description: `リセットまでの日数（1-365、デフォルト: 365）。`,
          serverwide_quota_resets_in_success_title: `クォータリセット期間が更新されました`,
          serverwide_quota_resets_in_success_description: `サーバー全体のクォータは **{days}** 日ごとにリセットされます。`,
        },
        textgen: {
          description: `このサーバーのテキスト生成トリガークォータを設定します。`,
          unlimited: `無制限`,
          daily_user_quota_description: `ユーザーごとの日次テキスト生成トリガー制限を設定します。`,
          daily_user_quota_limit_description: `ユーザー1人あたりの日次テキスト数（0=無制限、1-100、デフォルト: 0）。`,
          daily_user_quota_success_title: `ユーザークォータが更新されました`,
          daily_user_quota_success_description: `ユーザークォータが1日あたり **{limit}** 回のテキストトリガーに設定されました。`,
          serverwide_quota_description: `サーバー全体のテキスト生成トリガー上限を設定します。`,
          serverwide_quota_limit_description: `サーバー全体のテキスト数（0=無制限、1-99999、デフォルト: 0）。`,
          serverwide_quota_success_title: `サーバー全体のクォータが更新されました`,
          serverwide_quota_success_description: `サーバー全体のクォータが期間あたり **{limit}** 回のテキストトリガーに設定されました。`,
          serverwide_quota_resets_in_description: `サーバー全体のテキストクォータがリセットされるまでの日数を設定します。`,
          serverwide_quota_resets_in_days_description: `リセットまでの日数（1-365、デフォルト: 365）。`,
          serverwide_quota_resets_in_success_title: `クォータリセット期間が更新されました`,
          serverwide_quota_resets_in_success_description: `サーバー全体のテキストクォータは **{days}** 日ごとにリセットされます。`,
        },
        reset: {
          description: `画像/テキスト生成のクォータプールをリセットします。`,
          scope_description: `ユーザーの日次クォータをリセットするか、サーバー全体クォータをリセットするかを選択します。`,
          scope_choice_user: `ユーザー`,
          scope_choice_server: `サーバー`,
          quota_type_description: `リセットするクォータの種類を選択します。`,
          quota_type_choice_imagegen: `画像生成`,
          quota_type_choice_textgen: `テキスト生成`,
          user_select_title: `ユーザーを選択`,
          user_select_description: `日次クォータをリセットするユーザーを選択してください。`,
          user_select_placeholder: `ユーザーを選択...`,
          success_title: `クォータをリセットしました`,
          success_user_imagegen_description: `{user} の日次画像生成クォータ使用量をリセットしました。`,
          success_user_textgen_description: `{user} の日次テキスト生成トリガークォータ使用量をリセットしました。`,
          success_server_imagegen_description: `サーバー全体の画像生成クォータプールをリセットしました。`,
          success_server_textgen_description: `サーバー全体のテキスト生成トリガークォータプールをリセットしました。`,
        },
      },
      memberpermissions: {
        description: `管理者以外のメンバーが私に何を教えられるかを設定します。`,
        option_description: `メンバーが教えることができる記憶の種類。`,
        servermemories_option: `サーバーの記憶`,
        attributelist_option: `属性リスト`,
        sampledialogues_option: `サンプル対話`,
        permission_choice_servermemories: `サーバーの記憶`,
        permission_choice_attributelist: `属性リスト`,
        permission_choice_sampledialogues: `サンプル対話`,
        // セレクトメニューに表示する短い説明文
        servermemories_desc: "サーバー記憶の追加・削除",
        attributelist_desc: "性格属性の追加・削除",
        sampledialogues_desc: "サンプル対話の追加・削除",
        // チェックボックスセレクトメニューの文字列
        select_placeholder: "メンバーに許可することを選択...",
        select_embed_title: "メンバー教育権限",
        select_embed_description: "管理者以外のメンバーが**教えられる**ことを選択してください。チェックあり = 許可。",
        no_changes_title: "変更なし",
        no_changes_description: "すべての権限はすでに選択した値に設定されています。",
        timed_out_title: "タイムアウト",
        timed_out_description: "権限メニューがタイムアウトしました。変更は適用されませんでした。",
        set_description: `メンバーに対してこの権限を有効または無効にします。`,
        success_title: `メンバー権限が更新されました`,
        success_description: `**{count}** 件の権限を更新しました。`,
        enabled_success: `メンバーは \`{permission_type}\` を教えることができます。`,
        disabled_success: `メンバーはもう \`{permission_type}\` を教えることはできません。`,
        already_set_title: `権限は既に設定済みです`,
        already_enabled_description: `メンバーは既に \`{permission_type}\` を教えることが許可されています。`,
        already_disabled_description: `メンバーは既に \`{permission_type}\` を教えることが禁止されています。`,
      },
      avatar: {
        description: `このサーバーで選択したペルソナのアバターを設定または削除します。`,
        image_description: `アバターとして設定する画像（空白にすると選択したペルソナのアバターを削除）`,
        persona_modal_title: `ペルソナを選択`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `アバターを更新するペルソナを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        success_title: `アバターが更新されました`,
        success_description: `このサーバー用のアバターの更新に成功しました。`,
        success_alter_description: `ペルソナ「{persona_name}」のアバターを更新しました。`,
        removed_title: `アバターがリセットされました`,
        removed_description: `このサーバー用のアバターをデフォルトにリセットしました。`,
        removed_alter_description: `ペルソナ「{persona_name}」のアバターをリセットしました。`,
        invalid_image_title: `無効な画像`,
        invalid_image_description: `有効な画像ファイルを提供してください。`,
        file_too_large_title: `ファイルサイズが大きすぎます`,
        file_too_large_description: `画像ファイルが大きすぎます。最大ファイルサイズは8MBです。`,
        invalid_format_title: `無効な形式`,
        invalid_format_description: `PNG、JPG、JPEG、またはGIF画像ファイルを提供してください。`,
        conversion_error_title: `変換エラー`,
        conversion_error_description: `画像の処理に失敗しました。別の画像ファイルを試してください。`,
        api_error_title: `APIエラー`,
        api_error_description: `Discord APIを通じてアバターの更新に失敗しました。アバターを短時間で変更しすぎたことによるレート制限が原因であることが多いです。しばらく待ってから再度お試しください。`,
        error_download_timeout: `アバターのダウンロードが15秒後にタイムアウトしました。もう一度お試しください。`,
        error_api_timeout: `Discord API呼び出しが15秒後にタイムアウトしました。もう一度お試しください。`,
      },
      // 初期化サブコマンドグループ
      initialize: {
        description: `AI分析を使用してサーバー機能を初期化します`,
        expressions: {
          description: `AIビジョンを使用してすべてのカスタム絵文字とスタンプを分析・分類します`,
          // 成功メッセージ
          success_title: `絵文字とスタンプを初期化しました`,
          success_description: `{emoji_count}個の絵文字と{sticker_count}個のスタンプ（合計{total}個）を分析・分類しました。`,
          // エラーメッセージ
          model_incompatible_title: `互換性のないモデル`,
          model_incompatible_description: `現在のモデル（{model_name}）は{missing_capability}をサポートしていません。\`/config model text\`を使用して、画像ビジョンと構造化出力の両方をサポートするモデルに切り替えてください。`,
          already_initialized_title: `初期化するものがありません`,
          already_initialized_description: `すべての絵文字とスタンプはすでに分析・分類されています。`,
          partial_success_title: `部分的に成功`,
          partial_success_description: `{total}個の絵文字/スタンプのうち{successful}個を分析しました。{failed}個は処理されませんでした。残りの絵文字/スタンプを処理するには、このコマンドを再度実行してください。`,
          no_matches_title: `一致するものが見つかりません`,
          no_matches_description: `AIは絵文字/スタンプを分析しましたが、データベースと一致する結果が見つかりませんでした。処理エラーの可能性があります。`,
          llm_error_title: `AI分析に失敗しました`,
          llm_error_description: `AIモデルが絵文字/スタンプの分析中にエラーに遭遇しました。後でもう一度お試しください。`,
          validation_error_title: `無効なAI応答`,
          validation_error_description: `AIが無効な応答形式を返しました。これはモデルの問題である可能性があります。`,
          // 進行状況メッセージ
          progress_fetching: `未初期化の絵文字/スタンプを取得中...`,
          progress_building: `{emoji_count}個の絵文字と{sticker_count}個のスタンプが見つかりました...`,
          progress_analyzing: `{total}枚の画像を分析中...`,
          progress_analyzing_batch: `{total_uninitialized}枚のうち{batch_size}枚の画像を分析中（バッチ処理中 - 残りの絵文字/スタンプを処理するには、このコマンドを再度実行してください）`,
          progress_analyzing_gemini_batch: `{total_uninitialized}枚のうち{batch_size}枚の画像を分析中（Geminiはバッチ処理を行います - 残りの絵文字/スタンプを処理するには、このコマンドを再度実行してください）`,
          progress_saving: `結果をデータベースに保存中...`,
        },
      },
      // Matrixブリッジ管理
      matrix: {
        link: {
          description: `DiscordチャンネルをMatrixルームに双方向リレーでリンクします`,
          channel_description: `リンクするDiscordチャンネル`,
          room_description: `リンクするMatrixルームID（例：!abc:matrix.org）`,
          success_title: `Matrixルームをリンクしました`,
          success_description: `<#{channel_id}>が\`{room_id}\`とブリッジされました。TomoriのメッセージがMatrixルームに表示され、Matrixのメッセージもここに表示されます。

セットアップ手順、Matrix側で使えるコマンド、現在の制限一覧は {help_matrix} を確認してください。`,
          invalid_room_title: `無効なルームID`,
          invalid_room_description: `MatrixルームIDは\`!\`で始まり\`:\`を含む必要があります（例：\`!abc:matrix.org\`）。ルームIDを確認して再試行してください。`,
          join_failed_description: `<#{channel_id}>が\`{room_id}\`にリンクされましたが、Matrixルームに自動的に参加できませんでした。\`{bot_user_id}\`をルームに手動で招待し、必要なら {help_matrix} でセットアップ手順と制限一覧を確認してください。`,
          encrypted_room_title: `暗号化されたルームはリンクできません`,
          encrypted_room_description: `\`{room_id}\`はエンドツーエンド暗号化が有効です。Matrixの暗号化は一度設定すると無効にできないため、このルームはブリッジに使用できません。暗号化なしの新しいMatrixルームを作成し、代わりに\`{bot_user_id}\`を招待してください。`,
          matrix_not_configured_title: `Matrixブリッジ利用不可`,
          matrix_not_configured_description: `このBotインスタンスではMatrixブリッジが設定されていません。有効にするにはBot管理者にお問い合わせください。`,
        },
        unlink: {
          description: `DiscordチャンネルからMatrixブリッジリンクを削除します`,
          channel_description: `Matrixルームからリンクを解除するDiscordチャンネル`,
          success_title: `Matrixルームのリンクを解除しました`,
          success_description: `<#{channel_id}>はどのMatrixルームともブリッジされていません。`,
          not_linked_title: `リンクされていません`,
          not_linked_description: `<#{channel_id}>にはMatrixルームがリンクされていません。`,
        },
      },
      alwaysreply: {
        description: `メインペルソナの常時応答モードを切り替えます。`,
        enabled_title: `常時応答が有効になりました`,
        enabled_description: `**{persona_name}** はトリガーワードなしでもこのサーバーのすべてのメッセージに返信します。オルタペルソナは引き続きトリガーワードが必要です — オルタがトリガーされた場合、**{persona_name}** は二重応答を避けるために応答しません。`,
        disabled_title: `常時応答が無効になりました`,
        disabled_description: `**{persona_name}** はトリガーワード、メンション、またはリプライでのみ応答します。`,
      },
    },

    // 個人的なユーザー設定コマンド
    personal: {
      description: `あなたの個人的な設定を管理します`,
      privacy: {
        description: `個人記憶の保存とプライバシー設定を管理します`,

        // モーダルUI
        modal_title: `プライバシー設定`,
        select_label: `プライバシーレベル`,
        select_description: `プライバシー保護のレベルを選択してください`,
        select_placeholder: `プライバシーレベルを選択...`,

        // レベル 0 (最小限のプライバシー - 全機能)
        choice_minimal: `なし`,
        desc_minimal: `完全なパーソナライズ：記憶、ステータス、カスタムニックネーム、ボットのトリガーが可能。`,

        // レベル 1 (部分的なプライバシー)
        choice_partial: `部分的`,
        desc_partial: `メッセージは表示されますが、個人記憶/ステータスはAIに表示されません。`,

        // レベル 2 (完全なプライバシー - 最大限の保護)
        choice_full: `完全`,
        desc_full: `最大限のプライバシー：完全に非表示、メッセージ、記憶、ボットのトリガーはありません。`,

        // 成功/エラーメッセージ
        success_title: `プライバシー設定が更新されました`,
        success_description: `プライバシーレベルが\`{previous_value}\`から\`{value}\`に変更されました。

\`/personal privacy\`を使用していつでも変更できます。`,

        already_set_title: `変更はありません`,
        already_set_description: `プライバシーレベルは既に\`{value}\`に設定されています。`,

        invalid_value_description: `無効なプライバシーレベルが選択されました。もう一度お試しください。`,
      },

      language: {
        description: `インターフェースの優先言語を設定します。`,
        value_description: `インターフェースの優先言語を選択してください。`,
        choice_english: `英語`,
        choice_japanese: `日本語`,
        "value_choice_en-US": `英語`,
        value_choice_ja: `日本語`,
        invalid_value_title: `無効な言語`,
        invalid_value_description: `言語は次のいずれかでなければなりません: {supported}。`,
        already_set_title: `言語は既に設定済みです`,
        already_set_description: `あなたの言語設定は既に \`{value}\` に設定されています。`,
        success_title: `言語が更新されました`,
        success_description: `あなたのインターフェース言語が \`{previous_value}\` から \`{value}\` に変更されました。`,
      },

      nickname: {
        description: `私があなたを呼ぶ名前を変更します。`,
        option_description: `私があなたに使用すべきニックネーム（2〜32文字）。`,
        invalid_length_title: `無効なニックネームの長さ`,
        invalid_length: `ニックネームは {min}〜{max} 文字でなければなりません。`,
        success_title: `個人的なニックネームが更新されました`,
        success_description: `わかりました、これからはあなたのことを '{new_nickname}' と呼びます（以前は '{old_nickname}' でした）。`,
        success_but_disabled_description: `わかりました、あなたのことを '{new_nickname}' と呼ぶことを覚えておきます（以前は '{old_nickname}' でした）。

**警告:** 現在、このサーバーではパーソナライズが無効になっているため、このニックネームはここでは使用しません。パーソナライズが有効になっている他のサーバーでは使用します。`,
      },

      impersonate: {
        description: `ユーザーなりすまし設定を管理します。`,
        prompt: {
          description: `ユーザーなりすまし返信用の再利用プロンプトを設定します。`,
          modal_title: `ユーザーなりすましプロンプト`,
          prompt_label: `ペルソナプロンプト`,
          prompt_description: `あなたのなりすましが呼び出されたときに使われます。空欄で送信するとクリアされます。`,
          prompt_placeholder: `砕けた口調で、短めに、全部小文字多め、友達には少しだけ煽り気味で...`,
          success_title: `なりすましプロンプトを更新しました`,
          success_description: `今後はどこでも、ユーザーなりすまし返信でこのプロンプトが使われます。`,
          cleared_title: `なりすましプロンプトをクリアしました`,
          cleared_description: `ユーザーなりすましプロンプトを削除しました。`,
          already_set_title: `変更はありません`,
          already_set_description: `ユーザーなりすましプロンプトは既にその内容に設定されています。`,
          already_cleared_title: `プロンプト未設定`,
          already_cleared_description: `現在、ユーザーなりすましプロンプトは設定されていません。`,
        },
      },

      stm: {
        description: `STM（短期記憶）の設定を構成します`,
        option_description: `設定するSTM項目を選んでください`,
        crossserver_option: `サーバー間STM共有`,
        clear_option: `個人用STMをクリア`,
        crossserver: {
          title: `サーバー間STM共有`,
          enabled: `サーバー間STM共有が**有効**になりました。他のサーバーでのあなたの会話を参照できるようになります。`,
          disabled: `サーバー間STM共有が**無効**になりました。このサーバーでのあなたの会話のみを参照します。`,
        },
        clear: {
          title: `STMがクリアされました`,
          success: `ユーザー固有のSTMがすべてのチャンネルでクリアされました。`,
        },
      },
    },

    // Tomoriに教えるためのコマンド
    teach: {
      sampledialogue: {
        description: `私がどのように応答すべきかの例として、ユーザー/ボットの対話ペアを追加します。`,
        teaching_disabled_title: `サンプル対話の教育が無効です`,
        teaching_disabled_description: `現在、このサーバーではメンバーがサンプル対話を教える・取り除くことは許可されていません。\`サーバー管理\`権限を持つメンバーが\`/config memberpermissions\`でこれを有効にできます。`,
        modal_title: `サンプル対話の追加`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `この対話を追加するペルソナを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        user_input_label: `ユーザーのセリフ`,
        user_input_description: `任意: 単発入力。.txt一括時は空欄にしてください。`,
        user_input_placeholder: `好きな食べ物は何ですか？`,
        bot_input_label: `私の応答`,
        bot_input_description: `任意: 単発入力。.txt一括時は空欄にしてください。`,
        bot_input_placeholder: `わ、わたしはマンゴーが好きです…`,
        batch_file_label: `一括 .txt ファイル`,
        batch_file_description: `任意: 2行で1組。1行目{user}:/{{user}}:, 2行目{bot}:/{{char}}:`,
        no_input_title: `入力がありません`,
        no_input_description: `手入力2欄を両方入力するか、.txtをアップロードしてください。`,
        manual_pair_required_description: `手入力は「ユーザーのセリフ」と「私の応答」の両方が必要です。`,
        invalid_file_title: `無効なファイル`,
        invalid_file_description: `.txtファイルをアップロードしてください。`,
        file_too_large_description: `.txtファイルが大きすぎます。最大 {max_size} MB です。`,
        download_failed_description: `アップロードされたファイルのダウンロードに失敗しました。もう一度お試しください。`,
        invalid_batch_format_title: `一括形式が無効です`,
        invalid_batch_format_description: `{line_number} 行目の形式が無効です。想定プレフィックス: {expected_prefix}`,
        duplicate_title: `新規の対話がありません`,
        duplicate_description: `入力された対話ペアはすべて既存です。`,
        limit_exceeded_title: `サンプル対話上限に達しました`,
        limit_exceeded_description: `このサーバーはサンプル対話の上限 {max_allowed} 個に達しました（現在 {current_count} 個）。新しいものを追加する前に、\`/forget sampledialogue\`でいくつかのサンプル対話を削除してください。`,
        batch_limit_exceeded_title: `一括インポートが上限超過`,
        batch_limit_exceeded_description: `インポートに {import_count} 枠必要ですが、上限 {max_allowed} / 現在 {current_count} です。{remove_count} 件削除してから再試行してください。`,
        user_input_too_long_title: `ユーザー入力が長すぎます`,
        user_input_too_long_description: `ユーザー入力が長すぎます（{current_length} 文字）。最大許容長は {max_allowed} 文字です。`,
        bot_input_too_long_title: `ボットの応答が長すぎます`,
        bot_input_too_long_description: `ボットの応答が長すぎます（{current_length} 文字）。最大許容長は {max_allowed} 文字です。`,
        success_title: `サンプル対話が追加されました`,
        success_description: `新しいサンプル対話ペアを正常に追加しました:

**ユーザー:**
> {user_input}

**私:**
> {bot_input}`,
        batch_success_title: `サンプル対話を追加しました`,
        batch_success_description: `{added_count} 件のサンプル対話ペアを追加しました。`,
      },
      attribute: {
        description: `このサーバーでの私を表す人格属性を追加します。`,
        teaching_disabled_title: `属性の教育が無効です`,
        teaching_disabled_description: `現在、このサーバーではメンバーが人格属性を教える・取り除くことは許可されていません。\`サーバー管理\`権限を持つメンバーが\`/config memberpermissions\`でこれを有効にできます。`,
        modal_title: `人格属性の追加`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `この属性を追加するペルソナを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        modal_description: `このサーバーでの私の人格特性。名前のプレースホルダーとして使用する場合は\`{bot}\`を使用してください。`,
        attribute_input_label: `新しい属性`,
        attribute_input_description: `任意: 単発入力。.txt一括時は空欄にしてください。`,
        attribute_input_placeholder: `{bot}はマンゴーが好き`,
        batch_file_label: `一括 .txt ファイル`,
        batch_file_description: `任意: 空でない各行を1属性として追加します。`,
        no_input_title: `入力がありません`,
        no_input_description: `属性を入力するか、.txtをアップロードしてください。`,
        invalid_file_title: `無効なファイル`,
        invalid_file_description: `.txtファイルをアップロードしてください。`,
        file_too_large_description: `.txtファイルが大きすぎます。最大 {max_size} MB です。`,
        download_failed_description: `アップロードされたファイルのダウンロードに失敗しました。もう一度お試しください。`,
        duplicate_title: `重複した属性`,
        duplicate_description: `この属性 '{attribute}' は既に私の属性リストにあります。`,
        limit_exceeded_title: `属性上限に達しました`,
        limit_exceeded_description: `このサーバーは属性の上限 {max_allowed} 個に達しました（現在 {current_count} 個）。新しいものを追加する前に、\`/forget attribute\`でいくつかの属性を削除してください。`,
        batch_limit_exceeded_title: `一括インポートが上限超過`,
        batch_limit_exceeded_description: `インポートに {import_count} 枠必要ですが、上限 {max_allowed} / 現在 {current_count} です。{remove_count} 件削除してから再試行してください。`,
        content_too_long_title: `属性の内容が長すぎます`,
        content_too_long_description: `属性の内容が長すぎます（{current_length} 文字）。最大許容長は {max_allowed} 文字です。`,
        success_title: `属性が追加されました`,
        success_description: `'{attribute}' を私の人格属性に正常に追加しました。`,
        batch_success_title: `属性を追加しました`,
        batch_success_description: `{added_count} 件の属性を追加しました。`,
      },
      document: {
        description: `Retrieval-Augmented Generationで参照できる文書を教えます。`,
        scope_description: `この文書をペルソナ専用（デフォルト）にするか、サーバー全体で共有するかを選択します。`,
        scope_choice_persona: `ペルソナ`,
        scope_choice_serverwide: `サーバー全体`,
        persona_modal_title: `ペルソナを選択`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `この文書を保存するペルソナを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        persona_description: `scopeがペルソナのときの対象ペルソナ名（未指定時はメイン）。`,
        name_description: `文書の名前（選択したスコープ内で一意）。`,
        file_description: `文書ファイルをアップロード（.txt, .md, .pdf）。`,
        rag_disabled_title: `ドキュメントRAGが無効です`,
        rag_disabled_description: `非本番環境では文書の参照が無効です。.env に \`ACTIVATE_LOCAL_RAG=true\` を設定して有効化してください。`,
        teaching_disabled_title: `ドキュメントの教育が無効です`,
        teaching_disabled_description: `現在、このサーバーではメンバーが文書を教える・削除することは許可されていません。\`サーバー管理\`権限を持つメンバーが\`/server memberpermissions\`で有効にできます。`,
        no_embedding_model_title: `埋め込みモデルが設定されていません`,
        no_embedding_model_description: `このプロバイダーには埋め込みモデルが設定されていません。\`/config model embedding\`で設定してください。`,
        no_api_key_title: `APIキーがありません`,
        no_api_key_description: `文書を埋め込むにはAPIキーが必要です。\`/config apikey set\`を使用してください。`,
        invalid_name_title: `無効な文書名`,
        invalid_name_description: `有効な文書名を入力してください（1〜64文字）。`,
        duplicate_title: `文書名が既に存在します`,
        duplicate_description: `「{name}」という名前の文書は既に存在します。別の名前を選んでください。`,
        limit_exceeded_title: `文書の上限に達しました`,
        limit_exceeded_description: `このスコープ（{scope}）は文書の上限 {max_allowed} 件に達しました（現在 {current_count} 件）。\`/forget document\`で削除してください。`,
        invalid_file_title: `無効なファイル`,
        invalid_format: `.txt / .md / .pdf のファイルをアップロードしてください。`,
        file_too_large_title: `ファイルが大きすぎます`,
        file_too_large_description: `最大ファイルサイズは {max_size} MB です。`,
        download_failed_title: `ダウンロードに失敗しました`,
        download_failed_description: `アップロードされたファイルのダウンロードに失敗しました。もう一度試してください。`,
        empty_title: `文書が空です`,
        empty_description: `読み取れるテキストが見つかりませんでした。`,
        too_long_title: `文書が長すぎます`,
        too_long_description: `文書のテキストが長すぎます。最大 {max_length} 文字です。`,
        too_many_chunks_title: `チャンクが多すぎます`,
        too_many_chunks_description: `チャンク数が上限を超えました。1文書あたり最大 {max_chunks} チャンクです。`,
        server_chunk_limit_title: `サーバーのチャンク上限に達しました`,
        server_chunk_limit_description: `このスコープ（{scope}）のチャンク上限 {max_chunks} を超えるため追加できません。先に文書を削除してください。`,
        success_title: `文書を追加しました`,
        success_description: `**{name}** を {scope} に保存しました（{chunk_count} チャンク）。`,
        persona_scope_mismatch: `personaオプションはscopeが「ペルソナ」のときだけ指定できます。`,
        scope_label_persona: `ペルソナ「{persona_name}」`,
        scope_label_serverwide: `サーバー全体`,
      },
      history: {
        description: `AIを使ってこのチャンネルのメッセージ履歴から知識を抽出します。`,
        name_description: `生成するドキュメントの名前（選択したスコープ内でユニークである必要があります）。`,
        scope_description: `知識のスコープを選択: ペルソナ（デフォルト）、自動（ペルソナ検出）、またはグローバル。`,
        scope_choice_persona: `ペルソナ`,
        scope_choice_automatic: `自動`,
        scope_choice_global: `グローバル`,
        rag_disabled_title: `ドキュメントRAGが無効です`,
        rag_disabled_description: `非本番環境では文書の参照が無効です。.env に \`ACTIVATE_LOCAL_RAG=true\` を設定して有効化してください。`,
        no_permission_title: `権限がありません`,
        no_permission_description: `チャンネル履歴を抽出するには**サーバー管理**権限が必要です。`,
        model_incompatible_title: `モデルが非対応です`,
        model_incompatible_description: `現在のモデルは構造化出力をサポートしていないため、履歴抽出に使用できません。\`/config model text\`で対応モデルに切り替えてください。`,
        no_embedding_model_title: `埋め込みモデルが未設定です`,
        no_embedding_model_description: `埋め込みモデルが設定されていません。\`/config model embedding\`で設定してください。`,
        no_api_key_title: `APIキーが未設定です`,
        no_api_key_description: `履歴の抽出と埋め込みにはAPIキーが必要です。\`/config apikey set\`で設定してください。`,
        no_messages_title: `メッセージが見つかりません`,
        no_messages_description: `このチャンネルには知識を抽出できるメッセージがありません。`,
        no_facts_extracted_title: `ファクトが抽出されませんでした`,
        no_facts_extracted_description: `AIはチャンネル履歴から有意義なファクトを抽出できませんでした。会話が短すぎるか、些細なメッセージのみの場合に発生します。`,
        duplicate_title: `ドキュメント名が既に存在します`,
        duplicate_description: `\`{name}\`という名前のドキュメントがこのスコープに既に存在します。別の名前を選んでください。`,
        limit_exceeded_title: `ドキュメント上限に達しました`,
        limit_exceeded_description: `このスコープ（{scope}）には既に{current_count}件のドキュメントがあります（最大{max_allowed}件）。\`/forget document\`または\`/forget history\`で削除してから追加してください。`,
        server_chunk_limit_title: `サーバーのチャンク上限に達しました`,
        server_chunk_limit_description: `このスコープ（{scope}）のチャンク上限 {max_chunks} を超えるため追加できません。先に文書を削除してください。`,
        progress_fetching: `チャンネルメッセージを取得中...`,
        progress_extracting: `{message_count}件のメッセージから知識を抽出中（ウィンドウ {current}/{total}）...`,
        progress_embedding: `{fact_count}件のファクトの埋め込みを生成中...`,
        success_title: `履歴を抽出しました`,
        success_description: `**{message_count}**件のメッセージから**{fact_count}**件のファクトを抽出し、**{name}**として{scope}に保存しました（{chunk_count}チャンク）。`,
        success_automatic_description: `**{message_count}**件のメッセージから**{fact_count}**件のファクトを抽出しました。\n\n{persona_list}`,
        success_automatic_persona_line: `**{persona_name}**: **{doc_name}**として保存（{chunk_count}チャンク）`,
        success_automatic_global_fallback: `ペルソナが検出されませんでした。**{name}**としてサーバー全体スコープに保存しました。`,
        scope_label_persona: `ペルソナ「{persona_name}」`,
        scope_label_global: `サーバー全体`,
      },
      personaprompt: {
        description: `sysprompt の後ろに追記するペルソナ専用プロンプトを設定します`,
        no_permission_title: `🔴 権限がありません`,
        no_permission_description: `ペルソナプロンプトを設定するには**サーバー管理**権限が必要です。`,
        persona_select_label: `ペルソナ`,
        persona_select_description: `更新するペルソナを選択してください。`,
        persona_select_placeholder: `ペルソナを選択...`,
        main_persona_description: `メインペルソナ`,
        alter_persona_description: `オルタペルソナ`,
        modal_title: `ペルソナプロンプトを設定`,
        prompt_label: `ペルソナプロンプト`,
        prompt_description: `この内容は対象ペルソナのシステムプロンプト後に追記されます。`,
        prompt_placeholder: `例: ベテラン戦術家のように、簡潔で落ち着いた口調で話して。`,
        success_title: `ペルソナプロンプトを更新しました`,
        success_description: `「{persona_name}」のペルソナプロンプトを更新しました。`,
      },
      memory: {
        description: `私の記憶を管理`,
        personal: {
          description: `どのサーバーでも私が覚えているあなたの個人的な記憶を追加します。`,
          scope_description: `記憶のスコープ: ペルソナのみ（デフォルト）または全ペルソナ/サーバー共通`,
          scope_choice_persona: `ペルソナの記憶（デフォルト）`,
          scope_choice_global: `グローバル記憶（全ペルソナ/サーバー）`,
          modal_title: `個人的な記憶の追加`,
          persona_select_label: `ペルソナ`,
          persona_select_description: `この記憶を適用するペルソナを選択してください。`,
          persona_select_placeholder: `ペルソナを選択...`,
          main_persona_description: `メインペルソナ`,
          alter_persona_description: `オルタペルソナ`,
          modal_description: `どのサーバーでも私が覚えているあなたの記憶。`,
          memory_input_label: `新しい個人的な記憶`,
          memory_input_description: `任意: 単発入力。.txt一括時は空欄にしてください。`,
          memory_input_placeholder: `{user}はマンゴーが好き`,
          batch_file_label: `一括 .txt ファイル`,
          batch_file_description: `任意: 空でない各行を1記憶として追加します。`,
          no_input_title: `入力がありません`,
          no_input_description: `記憶を入力するか、.txtをアップロードしてください。`,
          invalid_file_title: `無効なファイル`,
          invalid_file_description: `.txtファイルをアップロードしてください。`,
          file_too_large_description: `.txtファイルが大きすぎます。最大 {max_size} MB です。`,
          download_failed_description: `アップロードされたファイルのダウンロードに失敗しました。もう一度お試しください。`,
          duplicate_title: `重複した個人的な記憶`,
          duplicate_description: `この記憶 '{memory}' は既にあなたの個人的な記憶にあります。`,
          limit_exceeded_title: `個人的な記憶の上限に達しました`,
          limit_exceeded_description: `あなたは個人的な記憶の上限 {max_allowed} 件に達しました（現在 {current_count} 件）。新しい記憶を追加する前に、\`/forget memory personal\`でいくつかの記憶を削除してください。`,
          batch_limit_exceeded_title: `一括インポートが上限超過`,
          batch_limit_exceeded_description: `インポートに {import_count} 枠必要ですが、上限 {max_allowed} / 現在 {current_count} です。{remove_count} 件削除してから再試行してください。`,
          content_too_long_title: `記憶の内容が長すぎます`,
          content_too_long_description: `記憶の内容が長すぎます。最大許容長は {max_length} 文字です。`,
          success_title: `個人的な記憶が追加されました`,
          success_description: `'{memory}' をあなたの個人的な記憶に正常に追加しました。`,
          batch_success_title: `個人的な記憶を追加しました`,
          batch_success_description: `{added_count} 件の個人的な記憶を追加しました。`,
          success_but_disabled_description: `'{memory}' をあなたの個人的な記憶に正常に追加しました。

**警告:** 現在、このサーバーではパーソナライズが無効になっているため、この記憶はここでは使用されません。パーソナライズが有効になっている他のサーバーでは引き続き利用可能です。`,
          batch_success_but_disabled_description: `{added_count} 件の個人的な記憶を追加しました。

**警告:** 現在、このサーバーではパーソナライズが無効になっているため、これらの記憶はここでは使用されません。パーソナライズが有効な他サーバーでは引き続き利用可能です。`,
          success_but_blacklisted_description: `'{memory}' をあなたの個人的な記憶に正常に追加しました。

**警告:** あなたは現在、このサーバーのパーソナライズ機能のブラックリストに登録されているため、この記憶はここでは使用されません。ブラックリストに登録されていない他のサーバーでは引き続き利用可能です。`,
          batch_success_but_blacklisted_description: `{added_count} 件の個人的な記憶を追加しました。

**警告:** あなたは現在、このサーバーのパーソナライズ機能のブラックリスト対象のため、これらの記憶はここでは使用されません。`,
          opted_out_error_title: `プライバシー保護が有効`,
          opted_out_error_description: `あなたはプライバシー上の理由から個人記憶の保存をオプトアウトしています。再び個人記憶を許可したい場合は、\`/personal privacy\`を使用してオプトインしてください。`,
        },
        server: {
          description: `私の知識ベースにサーバーの記憶を追加します。`,
          teaching_disabled_title: `サーバーの記憶の教育が無効です`,
          teaching_disabled_description: `現在、このサーバーではメンバーがサーバーの記憶を追加・取り除くすることは許可されていません。\`サーバー管理\`権限を持つメンバーが\`/config memberpermissions\`でこれを有効にできます。`,
          modal_title: `サーバーの記憶の追加`,
          persona_select_label: `ペルソナ`,
          persona_select_description: `このサーバー記憶を適用するペルソナを選択してください。`,
          persona_select_placeholder: `ペルソナを選択...`,
          main_persona_description: `メインペルソナ`,
          alter_persona_description: `オルタペルソナ`,
          modal_description: `このサーバーだけで私が覚えている記憶。`,
          memory_input_label: `新しいサーバーの記憶`,
          memory_input_description: `任意: 単発入力。.txt一括時は空欄にしてください。`,
          memory_input_placeholder: `このサーバーのメンバーはマンゴーが好き`,
          batch_file_label: `一括 .txt ファイル`,
          batch_file_description: `任意: 空でない各行を1記憶として追加します。`,
          no_input_title: `入力がありません`,
          no_input_description: `記憶を入力するか、.txtをアップロードしてください。`,
          invalid_file_title: `無効なファイル`,
          invalid_file_description: `.txtファイルをアップロードしてください。`,
          file_too_large_description: `.txtファイルが大きすぎます。最大 {max_size} MB です。`,
          download_failed_description: `アップロードされたファイルのダウンロードに失敗しました。もう一度お試しください。`,
          duplicate_title: `重複した記憶`,
          duplicate_description: `この記憶 '{memory}' は既にこのサーバーの私の記憶にあります。`,
          limit_exceeded_title: `サーバーの記憶の上限に達しました`,
          limit_exceeded_description: `このサーバーは記憶の上限 {max_allowed} 件に達しました（現在 {current_count} 件）。新しい記憶を追加する前に、\`/forget memory server\`でいくつかの記憶を削除してください。`,
          batch_limit_exceeded_title: `一括インポートが上限超過`,
          batch_limit_exceeded_description: `インポートに {import_count} 枠必要ですが、上限 {max_allowed} / 現在 {current_count} です。{remove_count} 件削除してから再試行してください。`,
          content_too_long_title: `記憶の内容が長すぎます`,
          content_too_long_description: `記憶の内容が長すぎます。最大許容長は {max_length} 文字です。`,
          success_title: `サーバーの記憶が追加されました`,
          success_description: `'{memory}' を私のサーバーの記憶に正常に追加しました。`,
          batch_success_title: `サーバーの記憶を追加しました`,
          batch_success_description: `{added_count} 件のサーバー記憶を追加しました。`,
        },
      },
    },

    // Tomoriに物事を忘れさせるためのコマンド
    forget: {
      sampledialogue: {
        description: `私の記憶からサンプルユーザー/ボットの対話ペアを削除します。`,
        modal_title: `サンプル対話の削除`,
        select_label: `削除する対話`,
        select_description: `削除する対話ペアを選択してください`,
        select_placeholder: `対話を選択...`,
        no_dialogues_title: `サンプル対話がありません`,
        no_dialogues: `削除するサンプル対話が保存されていません。\`/teach sampledialogue\`で追加してください。`,
        select_title: `サンプル対話の削除`,
        dialogue_label: `対話ペア`,
        success_title: `サンプル対話が削除されました`,
        success_description: `対話ペアを正常に削除しました: ユーザー: "{input}" → ボット: "{output}"`,
      },
      attribute: {
        description: `私の記憶から人格属性を削除します。`,
        modal_title: `属性の削除`,
        select_label: `削除する属性`,
        select_description: `私の人格から削除する属性を選択してください`,
        select_placeholder: `属性を選択...`,
        no_attributes_title: `属性がありません`,
        no_attributes: `削除する人格属性がありません。\`/teach attribute\`で追加してください。`,
        select_title: `属性の削除`,
        attribute_label: `属性`,
        success_title: `属性が削除されました`,
        success_description: `属性を正常に削除しました: "{attribute}"`,
      },
      document: {
        description: `サーバーの文書を削除します。`,
        scope_description: `ペルソナスコープかサーバー全体スコープかを選択します。`,
        scope_choice_persona: `ペルソナ`,
        scope_choice_serverwide: `サーバー全体`,
        modal_title: `文書の削除`,
        select_label: `削除する文書`,
        select_description: `削除する文書を選択してください`,
        select_placeholder: `文書を選択...`,
        rag_disabled_title: `ドキュメントRAGが無効です`,
        rag_disabled_description: `非本番環境では文書の参照が無効です。.env に \`ACTIVATE_LOCAL_RAG=true\` を設定して有効化してください。`,
        none_title: `文書がありません`,
        none_description: `このスコープには削除できる文書がありません。\`/teach document\`で追加してください。`,
        success_title: `文書が削除されました`,
        success_description: `文書を正常に削除しました: "{name}"`,
      },
      history: {
        description: `履歴抽出ドキュメントをサーバーの知識ベースから削除します。`,
        scope_description: `ペルソナスコープかサーバー全体スコープかを選択します。`,
        scope_choice_persona: `ペルソナ`,
        scope_choice_serverwide: `サーバー全体`,
        modal_title: `履歴ドキュメントの削除`,
        select_label: `削除するドキュメント`,
        select_description: `削除する履歴ドキュメントを選択してください`,
        select_placeholder: `ドキュメントを選択...`,
        rag_disabled_title: `ドキュメントRAGが無効です`,
        rag_disabled_description: `非本番環境では文書の参照が無効です。.env に \`ACTIVATE_LOCAL_RAG=true\` を設定して有効化してください。`,
        none_title: `履歴ドキュメントがありません`,
        none_description: `このスコープには削除できる履歴ドキュメントがありません。\`/teach history\`で抽出してください。`,
        success_title: `履歴ドキュメントが削除されました`,
        success_description: `履歴ドキュメントを正常に削除しました: "{name}"`,
      },
      personaprompt: {
        description: `ペルソナ専用プロンプトをクリアします`,
        no_permission_title: `🔴 権限がありません`,
        no_permission_description: `ペルソナプロンプトをクリアするには**サーバー管理**権限が必要です。`,
        success_title: `ペルソナプロンプトをクリアしました`,
        success_description: `「{persona_name}」のペルソナプロンプトをクリアしました。`,
      },
      reminder: {
        description: `リマインダーを削除します。`,
        modal_title: `リマインダーの削除`,
        select_label: `削除するリマインダー`,
        select_description: `削除するリマインダーを選択してください`,
        select_placeholder: `リマインダーを選択...`,
        no_reminders_title: `リマインダーがありません`,
        no_reminders: `削除するリマインダーがありません。リマインドしてほしい内容を私に伝えて設定できます。`,
        success_title: `リマインダーが削除されました`,
        success_description: `リマインダーを正常に削除しました: "{reminder_purpose}"`,
      },
      memory: {
        description: `私の記憶を管理`,
        personal: {
          description: `個人的な記憶を削除します。`,
          scope_description: `記憶のスコープ: ペルソナのみ（デフォルト）または全ペルソナ/サーバー共通`,
          scope_choice_persona: `ペルソナの記憶（デフォルト）`,
          scope_choice_global: `グローバル記憶（全ペルソナ/サーバー）`,
          modal_title: `個人的な記憶の削除`,
          select_label: `削除する記憶`,
          select_description: `削除する個人的な記憶を選択してください`,
          select_placeholder: `記憶を選択...`,
          no_memories_title: `個人的な記憶がありません`,
          no_memories: `あなたには個人的な記憶が保存されていません。\`/teach memory personal\`で追加してください。`,
          select_title: `個人的な記憶の削除`,
          memory_label: `個人的な記憶`,
          success_title: `個人的な記憶が削除されました`,
          success_description: `個人的な記憶を正常に削除しました: "{memory}"`,
          warning_disabled_title: `パーソナライズが無効です`,
          warning_disabled_description: `記憶は正常に削除されました。

**警告:** 現在、このサーバーではパーソナライズが無効になっているため、この変更はここでの私の行動に影響しません。パーソナライズが有効になっている他のサーバーでは反映されます。`,
        },
        server: {
          description: `私の知識からサーバーの記憶を削除します。`,
          modal_title: `サーバーの記憶の削除`,
          select_label: `削除する記憶`,
          select_description: `削除するサーバーの記憶を選択してください`,
          select_placeholder: `記憶を選択...`,
          no_memories_title: `サーバーの記憶がありません`,
          no_memories: `このサーバーにはサーバーの記憶が保存されていません。\`/teach memory server\`で追加してください。`,
          no_owned_memories: `あなたが所有していて削除できるサーバーの記憶はありません。`,
          memory_not_found: `選択された記憶が見つかりませんでした。`,
          select_title: `サーバーの記憶の削除`,
          memory_label: `サーバーの記憶`,
          success_title: `サーバーの記憶が削除されました`,
          success_description: `サーバーの記憶を正常に削除しました: "{memory}"`,
        },
      },
    },

    generate: {
      image: {
        // コマンド
        description: "Google GeminiまたはOpenRouterを使用してAI画像を生成する",

        // モーダル
        modal: {
          title: "画像生成のリクエスト",
          prompt_label: "画像プロンプト",
          prompt_description: "生成したい画像を説明してください",
          prompt_placeholder:
            "バナナを食べている、ショートヘアの可愛いエルフの美少女、マンガ風",
          image_upload_label: "参照画像（オプション）",
          image_upload_2_label: "参照画像2（オプション）",
          image_upload_3_label: "参照画像3（オプション）",
          image_upload_description:
            "画像間生成のために参照画像をアップロードできます",
          aspect_ratio_label: "アスペクト比",
          aspect_ratio_description: "希望するアスペクト比を選択してください",
          aspect_ratio_placeholder: "アスペクト比を選択...",
        },

        // 成功埋め込み
        success_title: "🟢 画像生成が完了しました！",
        success_description: "AI生成画像の準備ができました！",
        field_prompt: "プロンプト",
        field_model: "モデル",
        field_generation_time: "生成時間",
        field_aspect_ratio: "アスペクト比",

        // プロバイダー固有の警告
        zai_no_img2img_warning:
          "Z.aiは画像から画像への生成に対応していません。参照画像は無視されましたが、テキストプロンプトから画像は生成されます。",
        nvidia_no_img2img_warning:
          "NVIDIA NIMは画像から画像への生成に対応していません。参照画像は無視されましたが、テキストプロンプトから画像は生成されます。",

        // エラー
        disabled_title: "🔴 画像生成が無効です",
        disabled_description:
          "このサーバーでは画像生成が無効になっています。`/config permissions` で有効にできます（管理権限が必要）。",
        wrong_provider_title: "🔴 サポートされていないプロバイダー",
        wrong_provider_description:
          "画像生成にはネイティブ画像生成に対応したプロバイダーが必要です。現在のプロバイダーは**{current_provider}**です。",
        no_api_key_title: "🔴 APIキーがありません",
        no_api_key_description:
          "APIキーが設定されていません。`/config apikey set`を使用してください。",
        api_key_decrypt_failed_title: "🔴 APIキーエラー",
        api_key_decrypt_failed_description:
          "APIキーの復号化に失敗しました。`/config apikey set`を使用して再設定してください。",
        no_diffusion_model_title: "🔴 画像モデルがありません",
        no_diffusion_model_description:
          "プロバイダーに対して画像拡散モデルが設定されていません。",
        error_billing_title: "🔴 課金が必要です",
        error_billing_description:
          "画像生成を使用するには、APIキーの課金を有効にする必要があります。",
        error_safety_title: "🔴 コンテンツがブロックされました",
        error_safety_description:
          "プロンプトが安全フィルターによってブロックされました。別のプロンプトを試してください。",
        error_generation_failed_title: "🔴 生成に失敗しました",
        error_generation_failed_description: "画像生成に失敗しました: {error}",
        invalid_image_title: "🔴 無効な画像",
        invalid_image_description:
          "有効な画像ファイル（PNG、JPGなど）をアップロードしてください。",
        // クォータエラー
        quota_exceeded_title: "🔴 画像クォータを超過しました",
        quota_exceeded_description:
          "画像生成クォータに達しました。{reset_info}",
        user_quota_exceeded_description:
          "日次画像生成クォータに達しました。{reset_info}",
        serverwide_quota_exceeded_description:
          "このサーバーはこの期間の画像生成クォータに達しました。{reset_info}",
        quota_resets_in_hours: "クォータは {hours} 時間後にリセットされます。",
        quota_resets_in_days: "クォータは {days} 日後にリセットされます。",
        quota_exceeded_footer:
          "このクォータは、このサーバーの管理者が `/server quota` で設定しています。",
      },
    },
  },

  events: {
    // ボットがサーバーに追加されたときのメッセージ
    addBot: {
      rejoin_title: `TomoriBotが戻ってきました！`,
      rejoin_description: `このサーバーに再追加されたようです。以前の設定と人格はそのままです！\`/config\`、\`/teach\`、\`forget\`コマンドで私を管理できます。

			プロバイダーを変更したい場合は、\`/config apikeyset\`コマンドを使用してください。

			**TomoriBotを使用することで、[利用規約](https://github.com/Bredrumb/TomoriBot/blob/main/legal/ja/terms-of-service.md)と[プライバシーポリシー](https://github.com/Bredrumb/TomoriBot/blob/main/legal/ja/privacy-policy.md)に同意したことになります。**\`/legal terms\`と\`/legal privacy\`でいつでも確認できます。`,
      setup_prompt_title: `TomoriBotの追加が完了しました`,
      setup_prompt_description: `追加してくれてありがとうございます！始めるには、**サーバー管理**権限を持つ方が\`/config setup\`コマンドを実行して、私の初期の人格を選択し、AI機能を設定する必要があります。

			選択したAIプロバイダーのAPIキーの作成方法が不明な場合は、\`/help apikey\`コマンドを使用してください。APIキーは暗号化されて保存されますが、公開されているDiscordボットに提供することに不安がある場合（通常そうあるべきです）、[リポジトリのガイド](https://github.com/Bredrumb/TomoriBot)を使用してご自身でTomoriBotを実行することもできます。

			**TomoriBotを使用することで、[利用規約](https://github.com/Bredrumb/TomoriBot/blob/main/legal/ja/terms-of-service.md)と[プライバシーポリシー](https://github.com/Bredrumb/TomoriBot/blob/main/legal/ja/privacy-policy.md)に同意したことになります。**\`/legal terms\`と\`/legal privacy\`でいつでも確認できます。`,
    },
  },

  // リマインダーシステムメッセージ
  reminders: {
    // リマインダー設定時の確認埋め込み
    reminder_set_title: `⏰ {persona_nickname}がリマインダーを設定しました`,
    reminder_set_description: `{user_nickname}さんに「**{reminder_purpose}**」について\`{reminder_time}\`にリマインドします`,
    reminder_set_footer: `{time_remaining}後にメンションを送信します。リマインダーは\`/forget reminder\`で削除できます。`,
    reminder_set_footer_recurring: `最初のメンションは{time_remaining}後です。{repetition_interval_hours}時間ごとに繰り返します。リマインダーは\`/forget reminder\`で削除できます。`,

    // 繰り返しタスク設定（セルフリマインダー）
    recurring_task_set_title: `🔁 {persona_nickname}が定期タスクを設定しました`,
    recurring_task_set_description: `「**{reminder_purpose}**」を\`{reminder_time}\`から実行し、{repetition_interval_hours}時間ごとに繰り返します。`,
    recurring_task_set_footer: `リマインダーは\`/forget reminder\`で削除できます。`,

    // 1回のみのタスク設定（セルフリマインダー、繰り返しなし）
    task_set_title: `✅ {persona_nickname}がタスクを設定しました`,
    task_set_description: `「**{reminder_purpose}**」を\`{reminder_time}\`に実行します`,
    task_set_footer: `{time_remaining}後にタスクを実行します。リマインダーは\`/forget reminder\`で削除できます。`,

    // AI生成失敗時のフォールバック情報埋め込み - 生のリマインダー/タスク内容を表示
    reminder_triggered_title: `🔵 リマインダー通知`,
    task_triggered_title: `🔵 タスク通知`,
    triggered_description: `{reminder_purpose}`,
    triggered_footer: `生成中にエラーが発生したため、代わりに生のリマインダーを送信しました`,
  },

  // ツールメッセージ
  tools: {
    generate_image: {
      // クォータエラーメッセージ
      quota_exceeded_generic: `画像生成クォータを超過しました。`,
      user_quota_exceeded: `日次画像生成クォータに達しました。{reset_info}`,
      serverwide_quota_exceeded: `このサーバーはこの期間の画像生成クォータに達しました。{reset_info}`,
      quota_resets_in_hours: `クォータは {hours} 時間後にリセットされます。`,
      quota_resets_in_days: `クォータは {days} 日後にリセットされます。`,
      quota_remaining: `本日はあと {remaining} 枚の画像を生成できます。`,
    },
    generate_image_nai: {
      no_google_api_key: `インペインティングには画像セグメンテーション用のGoogle APIキーが必要です。/optionalkey google setで設定するか、Googleプロバイダーに切り替えてください。`,
      provider_quota_exceeded: `このアカウントではNovelAI画像生成クォータを使い切っています。Anlasを補充するか、クォータのリフレッシュ後に再試行してください。`,
      characters_require_v4: `キャラクター配置にはNovelAI V4以降の拡散モデルが必要です。`,
      character_requires_id_or_tags: `キャラクター項目 #{index} には id か tags のどちらかが必要です。`,
      invalid_character_identity: `無効なキャラクターIDです: {id}。persona:<id>、短い数値のペルソナID、またはDiscordのユーザースノーフレークを使用してください。`,
    },
  },

  // Matrixブリッジ - Matrixルームに転送されるDiscord埋め込みの簡潔なサマリー。
  // DiscordのリッチEmbed形式はMatrixではレンダリングできないため、
  // ツール結果の埋め込みは重要情報を伝える短いブラケット表記に変換されます。
  matrix: {
    embed: {
      server_memory_learned: `[「{memory}」を覚えました]`,
      personal_memory_learned: `[個人的なことを覚えました: 「{memory}」]`,
      server_memory_updated: `[記憶を更新しました: 「{memory}」]`,
      personal_memory_updated: `[個人的な記憶を更新しました: 「{memory}」]`,
      reminder_set: `[⏰ {description}]`,
      task_set: `[✅ {description}]`,
      recurring_task_set: `[🔁 {description}]`,
    },
    notices: {
      invited: `TomoriBotがこのルームに参加しました。

セットアップを完了するには:
1. Discordで、ブリッジしたいチャンネルで {link_command} を実行します。
2. {room_id_path} にあるこのルームの Internal Room ID を貼り付けます。

重要:
- このルームは非暗号化のままにしてください。
- リンク後は、このルームで普通に話しかければ使えます。
- Matrix側で使えるテキストコマンドは {kill_command} と {refresh_command} のみです。

詳しい手順と制限一覧は、Discordで {help_command} を確認してください。`,
      linked: `このルームはDiscordチャンネル {channel_name} とブリッジされました。

クイックヒント:
- ここで普通に話しかければTomoriBotと会話できます。
- Matrix側で使えるテキストコマンドは {kill_command} と {refresh_command} のみです。
- Slash Command、DM、ピン留めはMatrixから使えません。
- カスタム絵文字/Markdownは安定して描画されず、Embedはプレーンテキストとして転送されます。
- Matrixユーザーの個人メモリはサーバーメモリにフォールバックします。

詳しい手順と現在の制限は、Discordで {help_command} を確認してください。`,
    },
  },
};
