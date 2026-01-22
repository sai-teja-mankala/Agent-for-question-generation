import { Module } from "@nestjs/common";
import { AiModule } from "./ai/ai.module";
import { QuestionsModule } from "./questions/questions.module";

@Module({
  imports: [AiModule, QuestionsModule],
})
export class AppModule {}
