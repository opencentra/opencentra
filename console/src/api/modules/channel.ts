import { request } from "../request";
import type { ChannelConfig, SingleChannelConfig } from "../types";

export interface FeishuTestMessageRequest {
  receive_id: string;
  receive_id_type?: "open_id" | "chat_id" | "union_id";
  message?: string;
}

export interface FeishuTestMessageResponse {
  success: boolean;
  message: string;
}

export const channelApi = {
  listChannelTypes: () => request<string[]>("/config/channels/types"),

  listChannels: () => request<ChannelConfig>("/config/channels"),

  updateChannels: (body: ChannelConfig) =>
    request<ChannelConfig>("/config/channels", {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  getChannelConfig: (channelName: string) =>
    request<SingleChannelConfig>(
      `/config/channels/${encodeURIComponent(channelName)}`,
    ),

  updateChannelConfig: (channelName: string, body: SingleChannelConfig) =>
    request<SingleChannelConfig>(
      `/config/channels/${encodeURIComponent(channelName)}`,
      {
        method: "PUT",
        body: JSON.stringify(body),
      },
    ),

  testFeishuMessage: (body: FeishuTestMessageRequest) =>
    request<FeishuTestMessageResponse>("/config/channels/feishu/test", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
