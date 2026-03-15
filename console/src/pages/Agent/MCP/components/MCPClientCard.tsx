/**
 * MCP客户端卡片组件
 *
 * 功能说明：
 * 1. 显示MCP客户端的基本信息（名称、类型、状态、描述）
 * 2. 提供Test Connection按钮测试连接并获取工具列表
 * 3. 提供Enable/Disable切换按钮
 * 4. 提供Delete删除按钮
 * 5. 点击卡片可查看/编辑JSON配置
 *
 * 后端API：
 * - POST /api/mcp/{client_key}/test - 测试连接
 * - PUT /api/mcp/{client_key} - 更新配置
 * - DELETE /api/mcp/{client_key} - 删除客户端
 */
import { Card, Button, Modal, Tooltip } from "@agentscope-ai/design";
import { DeleteOutlined, LoadingOutlined } from "@ant-design/icons";
import { Server, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import type { MCPClientInfo, MCPTestResult } from "../../../../api/types";
import api from "../../../../api";
import { useTranslation } from "react-i18next";
import { useState } from "react";
import styles from "../index.module.less";

interface MCPClientCardProps {
  client: MCPClientInfo;
  onToggle: (client: MCPClientInfo, e: React.MouseEvent) => void;
  onDelete: (client: MCPClientInfo, e: React.MouseEvent) => void;
  onUpdate: (key: string, updates: any) => Promise<boolean>;
  isHovered: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

export function MCPClientCard({
  client,
  onToggle,
  onDelete,
  onUpdate,
  isHovered,
  onMouseEnter,
  onMouseLeave,
}: MCPClientCardProps) {
  const { t } = useTranslation();
  // JSON配置弹窗状态
  const [jsonModalOpen, setJsonModalOpen] = useState(false);
  // 删除确认弹窗状态
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  // 编辑中的JSON内容
  const [editedJson, setEditedJson] = useState("");
  // 是否处于编辑模式
  const [isEditing, setIsEditing] = useState(false);
  // 测试连接结果
  const [testResult, setTestResult] = useState<MCPTestResult | null>(null);
  // 是否正在测试连接
  const [isTesting, setIsTesting] = useState(false);
  // 是否显示工具列表弹窗
  const [showTools, setShowTools] = useState(false);

  // 判断客户端类型：Remote（HTTP/SSE）或 Local（stdio）
  const isRemote =
    client.transport === "streamable_http" || client.transport === "sse";
  const clientType = isRemote ? "Remote" : "Local";

  const handleToggleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggle(client, e);
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteModalOpen(true);
  };

  const confirmDelete = () => {
    setDeleteModalOpen(false);
    onDelete(client, null as any);
  };

  // 点击卡片打开JSON配置弹窗
  const handleCardClick = () => {
    const jsonStr = JSON.stringify(client, null, 2);
    setEditedJson(jsonStr);
    setIsEditing(false);
    setJsonModalOpen(true);
  };

  // 保存JSON配置
  const handleSaveJson = async () => {
    try {
      const parsed = JSON.parse(editedJson);
      const { key, ...updates } = parsed;
      const success = await onUpdate(client.key, updates);
      if (success) {
        setJsonModalOpen(false);
        setIsEditing(false);
      }
    } catch (error) {
      alert("Invalid JSON format");
    }
  };

  /**
   * 测试MCP客户端连接
   *
   * 调用后端API: POST /api/mcp/{client_key}/test
   * 返回：{ success, error, tools, connection_time_ms }
   */
  const handleTestConnection = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await api.testMCPClient(client.key);
      setTestResult(result);
      // 连接成功时自动弹出工具列表
      if (result.success) {
        setShowTools(true);
      }
    } catch (error: any) {
      setTestResult({
        success: false,
        error: error.message || "Connection failed",
        tools: [],
        connection_time_ms: 0,
      });
    } finally {
      setIsTesting(false);
    }
  };

  const clientJson = JSON.stringify(client, null, 2);

  return (
    <>
      <Card
        hoverable
        onClick={handleCardClick}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        className={`${styles.mcpCard} ${
          client.enabled ? styles.enabledCard : ""
        } ${isHovered ? styles.hover : styles.normal}`}
      >
        <div className={styles.cardHeader}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className={styles.fileIcon}>
              <Server style={{ color: "#1890ff", fontSize: 20 }} />
            </span>
            <Tooltip title={client.name}>
              <h3 className={styles.mcpTitle}>{client.name}</h3>
            </Tooltip>
            <span
              className={`${styles.typeBadge} ${
                isRemote ? styles.remote : styles.local
              }`}
            >
              {clientType}
            </span>
          </div>
          <div className={styles.statusContainer}>
            <span
              className={`${styles.statusDot} ${
                client.enabled ? styles.enabled : styles.disabled
              }`}
            />
            <span
              className={`${styles.statusText} ${
                client.enabled ? styles.enabled : styles.disabled
              }`}
            >
              {client.enabled ? t("common.enabled") : t("common.disabled")}
            </span>
          </div>
        </div>

        <div className={styles.description}>
          {client.description || "\u00A0"}
        </div>

        {/* Connection status indicator */}
        {testResult && (
          <div
            style={{
              marginTop: 8,
              padding: "8px 12px",
              borderRadius: 6,
              backgroundColor: testResult.success ? "#f6ffed" : "#fff2f0",
              borderLeft: `3px solid ${
                testResult.success ? "#52c41a" : "#ff4d4f"
              }`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              {testResult.success ? (
                <CheckCircle style={{ color: "#52c41a", fontSize: 16 }} />
              ) : (
                <XCircle style={{ color: "#ff4d4f", fontSize: 16 }} />
              )}
              <span
                style={{
                  fontSize: 12,
                  color: testResult.success ? "#52c41a" : "#ff4d4f",
                  fontWeight: 500,
                }}
              >
                {testResult.success
                  ? `${t("mcp.connectionSuccess")} (${
                      testResult.connection_time_ms
                    }ms)`
                  : t("mcp.connectionFailed")}
              </span>
            </div>
            {!testResult.success && testResult.error && (
              <div
                style={{
                  fontSize: 11,
                  color: "#999",
                  marginTop: 4,
                  wordBreak: "break-all",
                }}
              >
                {testResult.error}
              </div>
            )}
            {testResult.success && testResult.tools.length > 0 && (
              <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
                {t("mcp.toolsAvailable", { count: testResult.tools.length })}
              </div>
            )}
          </div>
        )}

        <div className={styles.cardFooter}>
          {/* Test connection button */}
          <Button
            type="link"
            size="small"
            icon={
              isTesting ? (
                <LoadingOutlined spin style={{ fontSize: 12 }} />
              ) : (
                <RefreshCw size={12} />
              )
            }
            onClick={handleTestConnection}
            className={styles.actionButton}
            disabled={isTesting}
          >
            {isTesting ? t("mcp.testing") : t("mcp.testConnection")}
          </Button>

          <Button
            type="link"
            size="small"
            onClick={handleToggleClick}
            className={styles.actionButton}
          >
            {client.enabled ? t("common.disable") : t("common.enable")}
          </Button>

          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            className={styles.deleteButton}
            onClick={handleDeleteClick}
            disabled={client.enabled}
          />
        </div>
      </Card>

      <Modal
        title={t("common.confirm")}
        open={deleteModalOpen}
        onOk={confirmDelete}
        onCancel={() => setDeleteModalOpen(false)}
        okText={t("common.confirm")}
        cancelText={t("common.cancel")}
        okButtonProps={{ danger: true }}
      >
        <p>{t("mcp.deleteConfirm")}</p>
      </Modal>

      <Modal
        title={`${client.name} - Configuration`}
        open={jsonModalOpen}
        onCancel={() => setJsonModalOpen(false)}
        footer={
          <div style={{ textAlign: "right" }}>
            <Button
              onClick={() => setJsonModalOpen(false)}
              style={{ marginRight: 8 }}
            >
              {t("common.cancel")}
            </Button>
            {isEditing ? (
              <Button type="primary" onClick={handleSaveJson}>
                {t("common.save")}
              </Button>
            ) : (
              <Button type="primary" onClick={() => setIsEditing(true)}>
                {t("common.edit")}
              </Button>
            )}
          </div>
        }
        width={700}
      >
        {isEditing ? (
          <textarea
            value={editedJson}
            onChange={(e) => setEditedJson(e.target.value)}
            className={styles.editJsonTextArea}
          />
        ) : (
          <pre className={styles.preformattedText}>{clientJson}</pre>
        )}
      </Modal>

      {/* Tools list modal */}
      <Modal
        title={`${client.name} - ${t("mcp.toolsList")}`}
        open={showTools}
        onCancel={() => setShowTools(false)}
        footer={
          <div style={{ textAlign: "right" }}>
            <Button onClick={() => setShowTools(false)}>
              {t("common.close")}
            </Button>
          </div>
        }
        width={800}
      >
        {testResult?.tools && testResult.tools.length > 0 ? (
          <div style={{ maxHeight: 500, overflow: "auto" }}>
            {testResult.tools.map((tool, index) => (
              <div
                key={index}
                style={{
                  padding: "12px",
                  borderBottom:
                    index < testResult.tools.length - 1
                      ? "1px solid #f0f0f0"
                      : "none",
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {tool.name}
                </div>
                <div style={{ fontSize: 12, color: "#666", marginBottom: 8 }}>
                  {tool.description || t("mcp.noDescription")}
                </div>
                {tool.input_schema &&
                  Object.keys(tool.input_schema).length > 0 && (
                    <details style={{ fontSize: 11 }}>
                      <summary style={{ cursor: "pointer", color: "#1890ff" }}>
                        {t("mcp.inputSchema")}
                      </summary>
                      <pre
                        style={{
                          fontSize: 10,
                          backgroundColor: "#f5f5f5",
                          padding: 8,
                          borderRadius: 4,
                          overflow: "auto",
                          maxHeight: 200,
                        }}
                      >
                        {JSON.stringify(tool.input_schema, null, 2)}
                      </pre>
                    </details>
                  )}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: 40, color: "#999" }}>
            {t("mcp.noTools")}
          </div>
        )}
      </Modal>
    </>
  );
}
