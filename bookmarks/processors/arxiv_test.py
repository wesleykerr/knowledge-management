# Standard Library
from unittest import mock

# Third Party
from absl.testing import absltest
from absl.testing import parameterized

# Project
from bookmarks.processors.arxiv import ArxivProcessor


class ArxivProcessorTest(parameterized.TestCase):
    def setUp(self):
        super().setUp()
        self.processor = ArxivProcessor()

    def test_extract_metadata_with_valid_html(self):
        # Given
        with open("bookmarks/processors/data/arxiv_test.html", "r") as input_io:
            html_content = input_io.read()

        # When
        metadata = self.processor.extract_metadata(html_content)

        # Then
        self.assertLen(metadata["authors"], 4)
        self.assertEqual(
            metadata["authors"],
            ["Reece Shuttleworth", "Jacob Andreas", "Antonio Torralba", "Pratyusha Sharma"],
        )
        self.assertEqual(
            metadata["abstract"],
            "Fine-tuning is a crucial paradigm for adapting pre-trained large language models to downstream tasks. Recently, methods like Low-Rank Adaptation (LoRA) have been shown to match the performance of fully fine-tuned models on various tasks with an extreme reduction in the number of trainable parameters. Even in settings where both methods learn similarly accurate models, \emph{are their learned solutions really equivalent?} We study how different fine-tuning methods change pre-trained models by analyzing the model's weight matrices through the lens of their spectral properties. We find that full fine-tuning and LoRA yield weight matrices whose singular value decompositions exhibit very different structure; moreover, the fine-tuned models themselves show distinct generalization behaviors when tested outside the adaptation task's distribution. More specifically, we first show that the weight matrices trained with LoRA have new, high-ranking singular vectors, which we call \emph{intruder dimensions}. Intruder dimensions do not appear during full fine-tuning. Second, we show that LoRA models with intruder dimensions, despite achieving similar performance to full fine-tuning on the target task, become worse models of the pre-training distribution and adapt less robustly to multiple tasks sequentially. Higher-rank, rank-stabilized LoRA models closely mirror full fine-tuning, even when performing on par with lower-rank LoRA models on the same tasks. These results suggest that models updated with LoRA and full fine-tuning access different parts of parameter space, even when they perform equally on the fine-tuned distribution. We conclude by examining why intruder dimensions appear in LoRA fine-tuned models, why they are undesirable, and how their effects can be minimized.",
        )
        self.assertEqual(metadata["arxiv_id"], "2410.21228")
        self.assertEqual(metadata["pdf_url"], "https://arxiv.org/pdf/2410.21228.pdf")

    def test_extract_metadata_handles_missing_elements(self):
        # Given
        html_content = "<div>Empty page</div>"

        # When
        metadata = self.processor.extract_metadata(html_content)

        # Then
        self.assertEmpty(metadata["authors"])
        self.assertEqual(metadata["abstract"], "")
        self.assertEqual(metadata["arxiv_id"], "")


if __name__ == "__main__":
    absltest.main()
