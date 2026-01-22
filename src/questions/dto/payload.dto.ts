import { IsObject, ValidateNested } from "class-validator";
import { Type } from "class-transformer";
import { GeneratedQuestionDto, QualityCheckDto } from "./question.dto";

export class QualityPayloadDto {
  @ValidateNested()
  @Type(() => GeneratedQuestionDto)
  question!: GeneratedQuestionDto;
}

export class FormatPayloadDto {
  @ValidateNested()
  @Type(() => GeneratedQuestionDto)
  question!: GeneratedQuestionDto;

  @ValidateNested()
  @Type(() => QualityCheckDto)
  quality?: QualityCheckDto;
}
