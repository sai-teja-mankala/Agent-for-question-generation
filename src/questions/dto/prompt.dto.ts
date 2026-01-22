import {
  IsArray,
  IsIn,
  IsNumber,
  IsOptional,
  IsString,
  ValidateNested,
} from "class-validator";
import { Type } from "class-transformer";

export class PromptRequestDto {
  @IsOptional()
  @IsString()
  locale?: string;

  @IsOptional()
  @IsString()
  sourceText?: string;

  @IsArray()
  @IsString({ each: true })
  learningObjectives!: string[];

  @IsOptional()
  @IsNumber()
  numberOfQuestions?: number;

  @IsOptional()
  @IsIn(["Beginner", "Intermediate", "Advanced"])
  difficultyLevel?: "Beginner" | "Intermediate" | "Advanced";

  @IsOptional()
  @IsIn(["MULTIPLE_CHOICE", "MULTIPLE_CHOICE_MULTI_SELECT", "MATCHING"])
  questionType?: "MULTIPLE_CHOICE" | "MULTIPLE_CHOICE_MULTI_SELECT" | "MATCHING";

  @IsOptional()
  perDifficulty?: boolean;

  @IsOptional()
  @IsNumber()
  numCorrectOptions?: number;

  @IsOptional()
  @IsNumber()
  numIncorrectOptions?: number;
}

export class PromptPayloadDto {
  @IsString()
  systemPrompt!: string;

  @IsString()
  userPrompt!: string;

  @IsString()
  responseFormat!: string;

  @IsString()
  learningObjective!: string;

  @IsOptional()
  @IsIn(["Beginner", "Intermediate", "Advanced"])
  difficultyLevel?: "Beginner" | "Intermediate" | "Advanced";

  @IsIn(["MULTIPLE_CHOICE", "MULTIPLE_CHOICE_MULTI_SELECT", "MATCHING"])
  questionType!: "MULTIPLE_CHOICE" | "MULTIPLE_CHOICE_MULTI_SELECT" | "MATCHING";
}

export class PromptBatchRequestDto {
  @IsOptional()
  @IsString()
  locale?: string;

  @IsOptional()
  @IsString()
  sourceText?: string;

  @IsArray()
  @IsString({ each: true })
  learningObjectives!: string[];

  @IsOptional()
  @IsNumber()
  numberOfQuestions?: number;

  @IsArray()
  @IsIn(["MULTIPLE_CHOICE", "MULTIPLE_CHOICE_MULTI_SELECT", "MATCHING"], {
    each: true,
  })
  questionTypes!: Array<
    "MULTIPLE_CHOICE" | "MULTIPLE_CHOICE_MULTI_SELECT" | "MATCHING"
  >;

  @IsOptional()
  @IsNumber()
  numCorrectOptions?: number;

  @IsOptional()
  @IsNumber()
  numIncorrectOptions?: number;
}

export class FormatConversionInputDto {
  @IsString()
  learningObjective!: string;

  @IsIn(["Beginner", "Intermediate", "Advanced"])
  levelOfQuiz!: "Beginner" | "Intermediate" | "Advanced";

  @IsIn(["MULTIPLE_CHOICE", "MULTIPLE_CHOICE_MULTI_SELECT", "MATCHING"])
  questionType!: "MULTIPLE_CHOICE" | "MULTIPLE_CHOICE_MULTI_SELECT" | "MATCHING";

  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => Object)
  questions!: Array<Record<string, unknown>>;
}
