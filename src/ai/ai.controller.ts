import { Body, Controller, Post } from "@nestjs/common";
import { ChatRequestDto } from "./dto/chat.dto";
import { OpenAiService } from "./openai.service";

@Controller("ai")
export class AiController {
  constructor(private readonly openAiService: OpenAiService) {}

  @Post("chat")
  async chat(@Body() payload: ChatRequestDto) {
    const completion = await this.openAiService.createChatCompletion(
      payload.messages,
      payload.model
    );
    return {
      id: completion.id,
      model: completion.model,
      created: completion.created,
      choices: completion.choices.map((choice) => ({
        index: choice.index,
        finish_reason: choice.finish_reason,
        message: choice.message,
      })),
    };
  }
}
