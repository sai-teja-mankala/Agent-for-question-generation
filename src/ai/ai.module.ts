import { Module } from "@nestjs/common";
import { AiController } from "./ai.controller";
import { OpenAiService } from "./openai.service";

@Module({
  controllers: [AiController],
  providers: [OpenAiService],
})
export class AiModule {}
