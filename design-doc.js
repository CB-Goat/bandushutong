/**
 * 「伴读书童」儿童课外阅读辅助工具
 * 产品设计文档 v1.0
 */

const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
        LevelFormat, PageBreak } = require('docx');
const fs = require('fs');

// 字体配置
const FONTS = {
    ascii: "Arial",
    hAnsi: "Arial",
    eastAsia: "Microsoft YaHei"
};

// 边框样式
const BORDER = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };

// 创建文档
const doc = new Document({
    styles: {
        default: {
            document: {
                run: {
                    font: FONTS,
                    size: 24  // 12pt
                }
            }
        },
        paragraphStyles: [
            {
                id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
                run: { size: 48, bold: true, color: "1A5F7A", font: FONTS },
                paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0, keepNext: false }
            },
            {
                id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
                run: { size: 36, bold: true, color: "2E86AB", font: FONTS },
                paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 1, keepNext: false }
            },
            {
                id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
                run: { size: 28, bold: true, color: "333333", font: FONTS },
                paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2, keepNext: false }
            }
        ]
    },
    numbering: {
        config: [
            {
                reference: "bullets",
                levels: [{
                    level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } }
                }]
            },
            {
                reference: "numbers",
                levels: [{
                    level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
                    style: { paragraph: { indent: { left: 720, hanging: 360 } } }
                }]
            }
        ]
    },
    sections: [{
        children: [
            // ===== 封面 =====
            new Paragraph({ spacing: { before: 2000 } }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({
                    text: "「伴读书童」",
                    bold: true,
                    size: 72,
                    color: "1A5F7A",
                    font: FONTS
                })]
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 200 },
                children: [new TextRun({
                    text: "儿童课外阅读辅助工具",
                    size: 48,
                    color: "2E86AB",
                    font: FONTS
                })]
            }),
            new Paragraph({ spacing: { before: 800 } }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({
                    text: "产品设计文档",
                    size: 32,
                    color: "666666",
                    font: FONTS
                })]
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 200 },
                children: [new TextRun({
                    text: "版本号：v1.0",
                    size: 24,
                    color: "999999",
                    font: FONTS
                })]
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                spacing: { before: 100 },
                children: [new TextRun({
                    text: "日期：2026年5月",
                    size: 24,
                    color: "999999",
                    font: FONTS
                })]
            }),
            new Paragraph({ children: [new PageBreak()] }),

            // ===== 目录 =====
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "目录", font: FONTS })]
            }),
            new Paragraph({
                spacing: { before: 200 },
                children: [
                    new TextRun({ text: "1. 产品概述", font: FONTS, size: 24 }),
                    new TextRun({ text: "  ..................  3", font: FONTS, size: 24, color: "999999" })
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "2. 用户需求分析", font: FONTS, size: 24 }),
                    new TextRun({ text: "  .................  4", font: FONTS, size: 24, color: "999999" })
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "3. 功能模块设计", font: FONTS, size: 24 }),
                    new TextRun({ text: "  .................  5", font: FONTS, size: 24, color: "999999" })
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "4. 技术架构方案", font: FONTS, size: 24 }),
                    new TextRun({ text: "  .................  8", font: FONTS, size: 24, color: "999999" })
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "5. 页面结构设计", font: FONTS, size: 24 }),
                    new TextRun({ text: "  ................. 10", font: FONTS, size: 24, color: "999999" })
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "6. 数据存储方案", font: FONTS, size: 24 }),
                    new TextRun({ text: "  ................  11", font: FONTS, size: 24, color: "999999" })
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "7. 开发计划", font: FONTS, size: 24 }),
                    new TextRun({ text: "  ....................  12", font: FONTS, size: 24, color: "999999" })
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "8. 风险评估与应对", font: FONTS, size: 24 }),
                    new TextRun({ text: "  .............  13", font: FONTS, size: 24, color: "999999" })
                ]
            }),
            new Paragraph({ children: [new PageBreak()] }),

            // ===== 1. 产品概述 =====
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "1. 产品概述", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                children: [new TextRun({ text: "1.1 产品定位", font: FONTS })]
            }),
            new Paragraph({
                numbering: { reference: "bullets", level: 0 },
                children: [new TextRun({ text: "产品名称：「伴读书童」（暂定）", font: FONTS })]
            }),
            new Paragraph({
                numbering: { reference: "bullets", level: 0 },
                children: [new TextRun({ text: "目标用户：6-14 岁儿童及家长", font: FONTS })]
            }),
            new Paragraph({
                numbering: { reference: "bullets", level: 0 },
                children: [new TextRun({ text: "核心价值：帮助孩子培养课外阅读习惯，让阅读更高效、更有趣", font: FONTS })]
            }),
            new Paragraph({
                numbering: { reference: "bullets", level: 0 },
                children: [new TextRun({ text: "技术形态：H5 网页应用（移动端优先）", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 300 },
                children: [new TextRun({ text: "1.2 核心功能", font: FONTS })]
            }),
            new Paragraph({
                numbering: { reference: "numbers", level: 0 },
                children: [new TextRun({ text: "文本导入：支持 TXT/EPUB/PDF 等常见课外书格式", font: FONTS })]
            }),
            new Paragraph({
                numbering: { reference: "numbers", level: 0 },
                children: [new TextRun({ text: "语音朗读 + 文字跟随：专业 TTS 预生成语音，朗读时文字同步高亮", font: FONTS })]
            }),
            new Paragraph({
                numbering: { reference: "numbers", level: 0 },
                children: [new TextRun({ text: "精美语句标注：对修辞手法、优美句子进行标记和分析", font: FONTS })]
            }),
            new Paragraph({
                numbering: { reference: "numbers", level: 0 },
                children: [new TextRun({ text: "章节梗概：阅读完每节后，生成内容摘要和要点提取", font: FONTS })]
            }),
            new Paragraph({
                numbering: { reference: "numbers", level: 0 },
                children: [new TextRun({ text: "阅读进度同步：支持多设备，数据存储在云端服务器", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 300 },
                children: [new TextRun({ text: "1.3 设计理念", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({
                    text: "• 最小阅读单位为一「节」：降低阅读门槛，每节控制在 300-800 字",
                    font: FONTS
                })]
            }),
            new Paragraph({
                children: [new TextRun({
                    text: "• 听读结合：通过语音朗读辅助阅读，降低阅读难度",
                    font: FONTS
                })]
            }),
            new Paragraph({
                children: [new TextRun({
                    text: "• 循序渐进：每节配有分析和总结，帮助理解吸收",
                    font: FONTS
                })]
            }),
            new Paragraph({
                children: [new TextRun({
                    text: "• 趣味激励：通过打卡、徽章等激励机制培养阅读习惯",
                    font: FONTS
                })]
            }),
            new Paragraph({ children: [new PageBreak()] }),

            // ===== 2. 用户需求分析 =====
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "2. 用户需求分析", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                children: [new TextRun({ text: "2.1 目标用户画像", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [2000, 7360],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "用户类型", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7360, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "特征描述", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "儿童用户", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7360, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "6-14岁，主要使用平板/手机；注意力有限；需要视觉和听觉双重刺激", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "家长用户", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7360, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "关注孩子阅读习惯培养；需要了解阅读进度；愿意参与引导", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 300 },
                children: [new TextRun({ text: "2.2 核心使用场景", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [2500, 6000, 1960],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "场景", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 6000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "描述", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 1960, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "频次", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "睡前阅读", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 6000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "孩子睡前听读15-30分钟，保护视力", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 1960, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "每天", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "碎片时间", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 6000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "上下学路上、等待时听一段朗读", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 1960, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "经常", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "亲子共读", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 6000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "家长和孩子一起讨论精美语句和章节内容", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 1960, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "偶尔", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            new Paragraph({ children: [new PageBreak()] }),

            // ===== 3. 功能模块设计 =====
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "3. 功能模块设计", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                children: [new TextRun({ text: "3.1 模块一：文本导入与解析", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [3000, 7000],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "功能项", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "说明", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "支持格式", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "TXT（纯文本）、EPUB（电子书）、PDF", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "章节解析", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "自动识别章节标题（支持常见格式：第X章、Chapter X、数字标题等）", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "小节分割", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "按段落/空行自动分割为「节」，每节 300-800 字", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "文本预处理", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "去除乱码、统一标点、段落格式化、繁简转换", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 300 },
                children: [new TextRun({ text: "3.2 模块二：语音朗读 + 文字跟随", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [3000, 7000],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "功能项", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "说明", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "语音生成", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "后端调用专业 TTS API 预生成音频文件，存储在服务器", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "语音选择", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "儿童友好音色（如阿里云童声、讯飞儿童音）", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "播放控制", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "播放/暂停/上一句/下一句/调节语速（0.5x-2x）", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "文字跟随", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "当前朗读句子高亮显示，自动滚动跟随定位", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "断点续读", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "自动保存播放位置，下次打开从断点继续", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 300 },
                children: [new TextRun({ text: "3.3 模块三：精美语句标注与分析", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [3000, 7000],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "功能项", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "说明", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "本地规则识别（基础）", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "修辞手法检测（比喻、拟人、排比）；长句/短句识别；引用匹配", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "AI 增强分析", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "调用大模型 API 生成语句赏析，用儿童易懂的语言解释", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "标注展示", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "精美语句用特殊样式标注（如橙色高亮），点击可查看分析", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 300 },
                children: [new TextRun({ text: "3.4 模块四：章节梗概与要点提取", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [3000, 7000],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "功能项", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "说明", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "触发时机", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "阅读完每节后自动弹出（或用户主动查看）", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "内容梗概", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "AI 生成 50-100 字的内容摘要", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "要点提取", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 7000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "提取 3-5 个核心要点（如：主要人物、关键事件、重要信息）", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            new Paragraph({ children: [new PageBreak()] }),

            // ===== 4. 技术架构方案 =====
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "4. 技术架构方案", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                children: [new TextRun({ text: "4.1 系统架构图", font: FONTS })]
            }),
            new Paragraph({
                spacing: { before: 200, after: 200 },
                children: [new TextRun({
                    text: "┌─────────────────────────────────────────────────────┐",
                    font: FONTS, size: 20
                })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "│                    前端 (H5 移动端)                 │", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "│         Vue 3 + Vant UI + HTML5 Audio              │", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "└─────────────────────────────────────────────────────┘", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "                          │", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "                          ▼", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "┌─────────────────────────────────────────────────────┐", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "│                   后端服务 (Python Flask)           │", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "│  • 用户认证    • 书籍管理    • TTS 调度    • AI 分析  │", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "└─────────────────────────────────────────────────────┘", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "                          │", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "          ┌─────────────────┼─────────────────┐", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "          ▼                 ▼                 ▼", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "   │  云数据库    │  │  TTS 服务    │  │  AI 大模型   │", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "   │ PostgreSQL  │  │ 阿里云/讯飞  │  │ 通义千问等   │", font: FONTS, size: 20 })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "   └─────────────┘  └─────────────┘  └─────────────┘", font: FONTS, size: 20 })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 400 },
                children: [new TextRun({ text: "4.2 技术选型明细", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [2500, 3000, 4500],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "技术领域", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "技术选型", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4500, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "说明", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "前端框架", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "Vue 3 + Vite", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "组件化开发，性能优秀", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "移动端组件库", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "Vant UI", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "轻量级移动端组件库", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "后端框架", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "Python Flask", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "轻量、易上手、快速开发", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "数据库", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "PostgreSQL + Redis", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "PostgreSQL 存数据，Redis 缓存会话", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "TTS 服务", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "阿里云 TTS / 讯飞 TTS", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "支持儿童音色，效果自然", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "AI 大模型", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "通义千问 / 文心一言", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "语句分析、内容梗概生成", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "文本解析", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "EPUB.js / PDF.js", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "处理电子书和 PDF 格式", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            new Paragraph({ children: [new PageBreak()] }),

            // ===== 5. 页面结构设计 =====
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "5. 页面结构设计", font: FONTS })]
            }),

            new Paragraph({
                spacing: { before: 200 },
                children: [new TextRun({
                    text: "应用包含以下主要页面：",
                    font: FONTS
                })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 200 },
                children: [new TextRun({ text: "5.1 首页（书架）", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 我的书籍列表（卡片形式展示）", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 导入新书按钮（+）", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 阅读统计入口", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 成就徽章展示", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 200 },
                children: [new TextRun({ text: "5.2 阅读页（核心页面）", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 顶部：书名 / 章节导航", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 中部：文本显示区（当前句子高亮、自动滚动）", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 底部：播放控制栏（播放/暂停、进度条、语速调节）", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 侧边栏：精美语句标注列表", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 底部弹窗：章节梗概 & 要点（阅读完成后）", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 200 },
                children: [new TextRun({ text: "5.3 设置页", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 语速调节", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 字体大小调节", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• AI 分析开关（开启/关闭）", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 阅读偏好设置", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 200 },
                children: [new TextRun({ text: "5.4 阅读统计页", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 累计阅读时长", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 已读书籍数量", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 连续阅读天数", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 阅读日历热力图", font: FONTS })]
            }),

            new Paragraph({ children: [new PageBreak()] }),

            // ===== 6. 数据存储方案 =====
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "6. 数据存储方案", font: FONTS })]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                children: [new TextRun({ text: "6.1 数据库设计", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [3000, 4000, 3000],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "数据表", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "说明", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "存储位置", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "users", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "用户信息", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "PostgreSQL", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "books", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "书籍元信息（不含内容）", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "PostgreSQL", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "book_sections", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "书籍章节和节信息", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "PostgreSQL", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "reading_progress", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "用户阅读进度", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "PostgreSQL", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "audio_files", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 4000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "TTS 音频文件索引", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "PostgreSQL + OSS", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                spacing: { before: 300 },
                children: [new TextRun({ text: "6.2 文件存储", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 原书文件（TXT/EPUB/PDF）：存储在 OSS 或本地服务器", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• TTS 音频文件：存储在 OSS，本地服务器备份", font: FONTS })]
            }),
            new Paragraph({
                children: [new TextRun({ text: "• 用户头像等静态资源：OSS 存储", font: FONTS })]
            }),

            new Paragraph({ children: [new PageBreak()] }),

            // ===== 7. 开发计划 =====
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "7. 开发计划", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [2000, 2500, 3000, 2500],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "阶段", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "功能范围", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "核心产出", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "预估工时", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "MVP 原型", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "文本导入 + 语音朗读 + 文字跟随", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "可运行的最小可用版本", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "1-2 周", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "V1.0 正式版", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "+ 章节解析 + 精美语句标注（本地规则）", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "完整阅读体验", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "2-3 周", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "V1.5 智能版", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "+ AI 语句赏析 + 内容梗概生成", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "智能分析增强", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "1-2 周", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "V2.0 产品化", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "+ 阅读进度 + 激励系统 + 多格式", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "完整产品", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 2500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "2-3 周", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            new Paragraph({ children: [new PageBreak()] }),

            // ===== 8. 风险评估与应对 =====
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "8. 风险评估与应对", font: FONTS })]
            }),

            new Table({
                width: { size: 100, type: WidthType.PERCENTAGE },
                columnWidths: [3500, 3500, 3000],
                rows: [
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "风险点", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "应对方案", bold: true, font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                shading: { fill: "E8F4F8", type: ShadingType.CLEAR },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "优先级", bold: true, font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "TTS 语音质量不佳", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "多尝试几家 TTS 服务，选择儿童音色最佳", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "高", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "TTS/API 费用成本", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "前期用免费额度，优化缓存策略减少调用", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "中", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "文本解析不准确", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "MVP 先支持 TXT 格式，后续优化解析算法", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "中", font: FONTS })] })]
                            })
                        ]
                    }),
                    new TableRow({
                        children: [
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "网络延迟影响体验", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3500, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "预加载下一节音频，离线缓存机制", font: FONTS })] })]
                            }),
                            new TableCell({
                                borders: BORDERS,
                                width: { size: 3000, type: WidthType.DXA },
                                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                                children: [new Paragraph({ children: [new TextRun({ text: "低", font: FONTS })] })]
                            })
                        ]
                    })
                ]
            }),

            // 文档结束
            new Paragraph({ spacing: { before: 600 } }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: "—— 文档结束 ——", font: FONTS, size: 20, color: "999999" })]
            })
        ]
    }]
});

// 生成文档
Packer.toBuffer(doc).then(buffer => {
    fs.writeFileSync('/workspace/reading-companion/伴读书童_产品设计文档_v1.0.docx', buffer);
    console.log('设计文档已生成：/workspace/reading-companion/伴读书童_产品设计文档_v1.0.docx');
});
