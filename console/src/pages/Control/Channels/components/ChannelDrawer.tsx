import {
  Alert,
  Drawer,
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Select,
  message,
} from "@agentscope-ai/design";
import { LinkOutlined, SendOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useState } from "react";
import type { FormInstance } from "antd";
import { getChannelLabel, type ChannelKey } from "./constants";
import { channelApi } from "../../../../api/modules/channel";
import styles from "../index.module.less";

interface ChannelDrawerProps {
  open: boolean;
  activeKey: ChannelKey | null;
  activeLabel: string;
  form: FormInstance<Record<string, unknown>>;
  saving: boolean;
  initialValues: Record<string, unknown> | undefined;
  isBuiltin: boolean;
  onClose: () => void;
  onSubmit: (values: Record<string, unknown>) => void;
}

// Doc URLs per channel (anchors on https://copaw.agentscope.io/docs/channels)
const CHANNEL_DOC_URLS: Partial<Record<ChannelKey, string>> = {
  dingtalk:
    "https://copaw.agentscope.io/docs/channels/#%E9%92%89%E9%92%89%E6%8E%A8%E8%8D%90",
  feishu: "https://copaw.agentscope.io/docs/channels/#%E9%A3%9E%E4%B9%A6",
  imessage:
    "https://copaw.agentscope.io/docs/channels/#iMessage%E4%BB%85-macOS",
  discord: "https://copaw.agentscope.io/docs/channels/#Discord",
  qq: "https://copaw.agentscope.io/docs/channels/#QQ",
  telegram: "https://copaw.agentscope.io/docs/channels/#Telegram",
};
const twilioConsoleUrl = "https://console.twilio.com";

export function ChannelDrawer({
  open,
  activeKey,
  activeLabel,
  form,
  saving,
  initialValues,
  isBuiltin,
  onClose,
  onSubmit,
}: ChannelDrawerProps) {
  const { t } = useTranslation();
  const label = activeKey ? getChannelLabel(activeKey) : activeLabel;

  // 飞书测试消息状态（消息文本不需要保存，保持独立state）
  const [testSending, setTestSending] = useState(false);
  const [testMessageText, setTestMessageText] = useState(
    "这是一条来自OpenCentra的测试消息🎉",
  );

  // 发送测试消息
  const handleSendTestMessage = async () => {
    // 从表单获取接收者ID和类型
    const receiveId = form.getFieldValue("notify_receive_id") || "";
    const receiveIdType =
      form.getFieldValue("notify_receive_id_type") || "open_id";

    if (!receiveId.trim()) {
      message.error(t("channels.feishuTestReceiveIdRequired"));
      return;
    }

    setTestSending(true);
    try {
      const response = await channelApi.testFeishuMessage({
        receive_id: receiveId.trim(),
        receive_id_type: receiveIdType,
        message: testMessageText || t("channels.feishuTestDefaultMessage"),
      });

      if (response.success) {
        message.success(t("channels.feishuTestSuccess"));
      } else {
        message.error(response.message || t("channels.feishuTestFailed"));
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      message.error(
        err?.response?.data?.detail || t("channels.feishuTestError"),
      );
    } finally {
      setTestSending(false);
    }
  };

  // Renders builtin channel-specific fields
  const renderBuiltinExtraFields = (key: ChannelKey) => {
    switch (key) {
      case "imessage":
        return (
          <>
            <Form.Item
              name="db_path"
              label="DB Path"
              rules={[{ required: true, message: "Please input DB path" }]}
            >
              <Input placeholder="~/Library/Messages/chat.db" />
            </Form.Item>
            <Form.Item
              name="poll_sec"
              label="Poll Interval (sec)"
              rules={[
                { required: true, message: "Please input poll interval" },
              ]}
            >
              <InputNumber min={0.1} step={0.1} style={{ width: "100%" }} />
            </Form.Item>
          </>
        );
      case "discord":
        return (
          <>
            <Form.Item name="bot_token" label="Bot Token">
              <Input.Password placeholder="Discord bot token" />
            </Form.Item>
            <Form.Item name="http_proxy" label="HTTP Proxy">
              <Input placeholder="http://127.0.0.1:18118" />
            </Form.Item>
            <Form.Item name="http_proxy_auth" label="HTTP Proxy Auth">
              <Input placeholder="user:password" />
            </Form.Item>
          </>
        );
      case "dingtalk":
        return (
          <>
            <Form.Item name="client_id" label="Client ID">
              <Input />
            </Form.Item>
            <Form.Item name="client_secret" label="Client Secret">
              <Input.Password />
            </Form.Item>
            <Form.Item
              name="dm_policy"
              label={t("channels.dmPolicy")}
              tooltip={t("channels.dmPolicyTooltip")}
              initialValue="open"
            >
              <Select
                options={[
                  { value: "open", label: t("channels.policyOpen") },
                  { value: "allowlist", label: t("channels.policyAllowlist") },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="group_policy"
              label={t("channels.groupPolicy")}
              tooltip={t("channels.groupPolicyTooltip")}
              initialValue="open"
            >
              <Select
                options={[
                  { value: "open", label: t("channels.policyOpen") },
                  { value: "allowlist", label: t("channels.policyAllowlist") },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="allow_from"
              label={t("channels.allowFrom")}
              tooltip={t("channels.allowFromTooltip")}
              initialValue={[]}
            >
              <Select
                mode="tags"
                placeholder={t("channels.allowFromPlaceholder")}
                tokenSeparators={[","]}
              />
            </Form.Item>
          </>
        );
      case "feishu":
        return (
          <>
            <Form.Item
              name="app_id"
              label="App ID"
              rules={[{ required: true }]}
            >
              <Input placeholder="cli_xxx" />
            </Form.Item>
            <Form.Item
              name="app_secret"
              label="App Secret"
              rules={[{ required: true }]}
            >
              <Input.Password placeholder="App Secret" />
            </Form.Item>
            <Form.Item name="encrypt_key" label="Encrypt Key">
              <Input placeholder="Optional, for event encryption" />
            </Form.Item>
            <Form.Item name="verification_token" label="Verification Token">
              <Input placeholder="Optional" />
            </Form.Item>
            <Form.Item name="media_dir" label="Media Dir">
              <Input placeholder="~/.copaw/media" />
            </Form.Item>

            <Alert
              type="info"
              showIcon
              message={t("channels.feishuTestInfo")}
              style={{ marginBottom: 16, marginTop: 16 }}
            />

            <Form.Item
              name="notify_receive_id"
              label={t("channels.feishuTestReceiveId")}
              help={t("channels.feishuTestReceiveIdRequired")}
            >
              <Input placeholder="ou_xxx" />
            </Form.Item>
            <Form.Item
              name="notify_receive_id_type"
              label={t("channels.feishuTestReceiveIdType")}
              initialValue="open_id"
            >
              <Select
                options={[
                  { value: "open_id", label: "open_id" },
                  { value: "chat_id", label: "chat_id" },
                  { value: "union_id", label: "union_id" },
                ]}
              />
            </Form.Item>
            <Form.Item label={t("channels.feishuTestMessage")}>
              <Input.TextArea
                rows={2}
                placeholder={t("channels.feishuTestDefaultMessage")}
                value={testMessageText}
                onChange={(e) => setTestMessageText(e.target.value)}
              />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                icon={<SendOutlined />}
                loading={testSending}
                onClick={handleSendTestMessage}
                disabled={!initialValues?.enabled || testSending}
              >
                {testSending
                  ? t("channels.feishuTestSending")
                  : t("channels.feishuTestSend")}
              </Button>
            </Form.Item>
          </>
        );
      case "qq":
        return (
          <>
            <Form.Item name="app_id" label="App ID">
              <Input />
            </Form.Item>
            <Form.Item name="client_secret" label="Client Secret">
              <Input.Password />
            </Form.Item>
          </>
        );
      case "telegram":
        return (
          <>
            <Form.Item name="bot_token" label="Bot Token">
              <Input.Password placeholder="Telegram bot token from BotFather" />
            </Form.Item>
            <Form.Item name="http_proxy" label="HTTP Proxy">
              <Input placeholder="http://127.0.0.1:18118" />
            </Form.Item>
            <Form.Item name="http_proxy_auth" label="HTTP Proxy Auth">
              <Input placeholder="user:password" />
            </Form.Item>
            <Form.Item
              name="show_typing"
              label="Show Typing"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </>
        );
      case "voice":
        return (
          <>
            <Alert
              type="info"
              showIcon
              message={t("channels.voiceSetupGuide")}
              style={{ marginBottom: 16 }}
            />
            <Form.Item
              name="twilio_account_sid"
              label={t("channels.twilioAccountSid")}
            >
              <Input placeholder="ACxxxxxxxx" />
            </Form.Item>
            <Form.Item
              name="twilio_auth_token"
              label={t("channels.twilioAuthToken")}
            >
              <Input.Password />
            </Form.Item>
            <Form.Item name="phone_number" label={t("channels.phoneNumber")}>
              <Input placeholder="+15551234567" />
            </Form.Item>
            <Form.Item
              name="phone_number_sid"
              label={t("channels.phoneNumberSid")}
              tooltip={t("channels.phoneNumberSidHelp")}
            >
              <Input placeholder="PNxxxxxxxx" />
            </Form.Item>
            <Form.Item name="tts_provider" label={t("channels.ttsProvider")}>
              <Input placeholder="google" />
            </Form.Item>
            <Form.Item name="tts_voice" label={t("channels.ttsVoice")}>
              <Input placeholder="en-US-Journey-D" />
            </Form.Item>
            <Form.Item name="stt_provider" label={t("channels.sttProvider")}>
              <Input placeholder="deepgram" />
            </Form.Item>
            <Form.Item name="language" label={t("channels.language")}>
              <Input placeholder="en-US" />
            </Form.Item>
            <Form.Item
              name="welcome_greeting"
              label={t("channels.welcomeGreeting")}
            >
              <Input.TextArea rows={2} />
            </Form.Item>
          </>
        );
      default:
        return null;
    }
  };

  // Renders custom channel fields as key-value editor
  const renderCustomExtraFields = (
    customInitialValues: Record<string, unknown> | undefined,
  ) => {
    if (!customInitialValues) return null;

    // Get extra fields (exclude base fields)
    const baseFields = [
      "enabled",
      "bot_prefix",
      "filter_tool_messages",
      "filter_thinking",
      "isBuiltin",
    ];
    const extraKeys = Object.keys(customInitialValues).filter(
      (k) => !baseFields.includes(k),
    );

    if (extraKeys.length === 0) return null;

    return (
      <>
        <div style={{ marginBottom: 8, fontWeight: 500 }}>Custom Fields</div>
        {extraKeys.map((fieldKey) => {
          const value = customInitialValues[fieldKey];
          const isBoolean = typeof value === "boolean";
          const isNumber = typeof value === "number";

          return (
            <Form.Item key={fieldKey} name={fieldKey} label={fieldKey}>
              {isBoolean ? (
                <Switch />
              ) : isNumber ? (
                <InputNumber style={{ width: "100%" }} />
              ) : (
                <Input />
              )}
            </Form.Item>
          );
        })}
      </>
    );
  };

  return (
    <Drawer
      width={420}
      placement="right"
      title={
        <div className={styles.drawerTitle}>
          <span>
            {label
              ? `${label} ${t("channels.settings")}`
              : t("channels.channelSettings")}
          </span>
          {activeKey && CHANNEL_DOC_URLS[activeKey] && (
            <Button
              type="text"
              size="small"
              icon={<LinkOutlined />}
              onClick={() => window.open(CHANNEL_DOC_URLS[activeKey], "_blank")}
              className={styles.dingtalkDocBtn}
            >
              {label} Doc
            </Button>
          )}
          {activeKey === "voice" && (
            <Button
              type="text"
              size="small"
              icon={<LinkOutlined />}
              onClick={() =>
                window.open(twilioConsoleUrl, "_blank", "noopener,noreferrer")
              }
              className={styles.dingtalkDocBtn}
            >
              {t("channels.voiceSetupLink")}
            </Button>
          )}
        </div>
      }
      open={open}
      onClose={onClose}
      destroyOnClose
    >
      {activeKey && (
        <Form
          form={form}
          layout="vertical"
          initialValues={initialValues}
          onFinish={onSubmit}
        >
          <Form.Item name="enabled" label="Enabled" valuePropName="checked">
            <Switch />
          </Form.Item>

          {activeKey !== "voice" && (
            <Form.Item name="bot_prefix" label="Bot Prefix">
              <Input placeholder="@bot" />
            </Form.Item>
          )}

          {activeKey !== "console" && (
            <>
              <Form.Item
                name="filter_tool_messages"
                label={t("channels.filterToolMessages")}
                valuePropName="checked"
                tooltip={t("channels.filterToolMessagesTooltip")}
              >
                <Switch />
              </Form.Item>
              <Form.Item
                name="filter_thinking"
                label={t("channels.filterThinking")}
                valuePropName="checked"
                tooltip={t("channels.filterThinkingTooltip")}
              >
                <Switch />
              </Form.Item>
            </>
          )}

          {isBuiltin
            ? renderBuiltinExtraFields(activeKey)
            : renderCustomExtraFields(initialValues)}

          <Form.Item>
            <div className={styles.formActions}>
              <Button onClick={onClose}>{t("common.cancel")}</Button>
              <Button type="primary" htmlType="submit" loading={saving}>
                {t("common.save")}
              </Button>
            </div>
          </Form.Item>
        </Form>
      )}
    </Drawer>
  );
}
