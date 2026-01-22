import OpenAI from "openai";

type AzureConfig = {
  endpoint: string;
  apiKey: string;
  deployment: string;
};

export class OpenAiService {
  private client: OpenAI | null = null;

  private getConfig(): AzureConfig {
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT;
    const apiKey = process.env.AZURE_OPENAI_API_KEY;
    const deployment = process.env.AZURE_OPENAI_DEPLOYMENT;

    const missing = [];
    if (!endpoint) missing.push("AZURE_OPENAI_ENDPOINT");
    if (!apiKey) missing.push("AZURE_OPENAI_API_KEY");
    if (!deployment) missing.push("AZURE_OPENAI_DEPLOYMENT");

    if (missing.length) {
      throw new Error(
        `Missing Azure OpenAI env vars: ${missing.join(", ")}`
      );
    }

    return { endpoint, apiKey, deployment };
  }

  private getClient(): OpenAI {
    if (this.client) return this.client;
    const { endpoint, apiKey } = this.getConfig();
    this.client = new OpenAI({
      baseURL: endpoint,
      apiKey,
    });
    return this.client;
  }

  async createChatCompletion(
    messages: OpenAI.ChatCompletionMessageParam[],
    model?: string
  ) {
    const { deployment } = this.getConfig();
    const client = this.getClient();
    return client.chat.completions.create({
      model: model || deployment,
      messages,
    });
  }
}
