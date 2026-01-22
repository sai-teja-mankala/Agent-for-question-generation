import { Body, Controller, Post } from "@nestjs/common";
import { PromptPayloadDto } from "./dto/prompt.dto";
import { QuestionsService } from "./questions.service";
import {
  FormatConversionInputDto,
  PromptBatchRequestDto,
  PromptRequestDto,
} from "./dto/prompt.dto";
import {
  GenerateQuestionInputDto,
  GeneratedQuestionDto,
  QualityCheckDto,
  ReqFormattedQuestionDto,
} from "./dto/question.dto";
import { FormatPayloadDto, QualityPayloadDto } from "./dto/payload.dto";

@Controller("questions")
export class QuestionsController {
  constructor(private readonly questionsService: QuestionsService) {}

  @Post("generate")
  generate(
    @Body() input: GenerateQuestionInputDto
  ): { question: GeneratedQuestionDto; quality: QualityCheckDto } {
    return this.questionsService.generateQuestion(input || {});
  }

  @Post("quality")
  quality(
    @Body() payload: QualityPayloadDto
  ): QualityCheckDto {
    return this.questionsService.checkQuality(payload.question);
  }

  @Post("format")
  format(
    @Body() payload: FormatPayloadDto
  ): ReqFormattedQuestionDto {
    const quality =
      payload.quality || this.questionsService.checkQuality(payload.question);
    return this.questionsService.toReqFormat(payload.question, quality);
  }

  @Post("prompts")
  prompts(@Body() input: PromptRequestDto): PromptPayloadDto {
    return this.questionsService.buildPromptPayload(input);
  }

  @Post("prompts/batch")
  promptsBatch(@Body() input: PromptBatchRequestDto): PromptPayloadDto[] {
    return this.questionsService.buildPromptBatch(input);
  }

  @Post("convert")
  convert(@Body() input: FormatConversionInputDto) {
    return this.questionsService.toResponseFormat(input);
  }
}
