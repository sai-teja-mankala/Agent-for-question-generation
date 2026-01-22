import {
  IsArray,
  IsBoolean,
  IsIn,
  IsNumber,
  IsOptional,
  IsString,
  ValidateNested,
} from "class-validator";
import { Type } from "class-transformer";

export class GenerateQuestionInputDto {
  @IsOptional()
  @IsString()
  topic?: string;

  @IsOptional()
  @IsString()
  stem?: string;

  @IsOptional()
  @IsString()
  answer?: string;

  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  distractors?: string[];

  @IsOptional()
  @IsIn(["easy", "medium", "hard"])
  difficulty?: "easy" | "medium" | "hard";
}

export class GeneratedQuestionDto {
  @IsString()
  topic!: string;

  @IsString()
  stem!: string;

  @IsString()
  answer!: string;

  @IsArray()
  @IsString({ each: true })
  distractors!: string[];

  @IsArray()
  @IsString({ each: true })
  choices!: string[];

  @IsIn(["easy", "medium", "hard"])
  difficulty!: "easy" | "medium" | "hard";
}

export class QualityCheckDto {
  @IsNumber()
  score!: number;

  @IsBoolean()
  isPassing!: boolean;

  @IsArray()
  @IsString({ each: true })
  issues!: string[];

  @IsArray()
  @IsString({ each: true })
  suggestions!: string[];
}

export class ReqFormattedQuestionMetadataDto {
  @IsIn(["easy", "medium", "hard"])
  difficulty!: "easy" | "medium" | "hard";

  @IsNumber()
  qualityScore!: number;
}

export class ReqFormattedQuestionBodyDto {
  @IsString()
  id!: string;

  @IsString()
  stem!: string;

  @IsArray()
  @IsString({ each: true })
  options!: string[];

  @IsString()
  answer!: string;
}

export class ReqFormattedQuestionDto {
  @ValidateNested()
  @Type(() => ReqFormattedQuestionMetadataDto)
  metadata!: ReqFormattedQuestionMetadataDto;

  @ValidateNested()
  @Type(() => ReqFormattedQuestionBodyDto)
  question!: ReqFormattedQuestionBodyDto;
}
