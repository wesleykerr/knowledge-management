---
parent: "[[Papers]]"
url: https://arxiv.org/abs/2408.04567
tags:
 - ai
 - 3d-scene-generation
 - diffusion-models
 - procedural-content-generation
 - game-development
 - controlnet
date: 2024-08-18T09:42
bookmark_date: 2024-08-18T09:42
---


### Summary
The document presents "Sketch2Scene," a novel pipeline designed to automatically generate interactive 3D game scenes from user-provided sketches and text prompts. The proposed method addresses the challenges of 3D content generation, particularly the lack of large-scale 3D scene datasets, by leveraging pre-trained 2D denoising diffusion models. The pipeline includes several key modules:

1. Sketch Guided Isometric Generation: This module uses a pre-trained diffusion model to convert casual user sketches into 2D isometric images, which serve as a conceptual representation of the intended 3D scene.

2. Visual Scene Understanding: The generated 2D image is analyzed to extract scene elements such as terrain heightmaps, texture splatmaps, and object instances. This data is crucial for accurately rendering the 3D environment.

3. Procedural 3D Scene Generation: Using the extracted data, the pipeline creates a fully interactive 3D scene that can be integrated into popular game engines like Unity. The method ensures that the generated scenes are highly detailed, interactive, and align closely with the user’s design intentions.

Extensive experiments demonstrate the effectiveness of Sketch2Scene in generating high-quality, game-ready 3D environments from simple user inputs. The paper also discusses the limitations of the current approach and potential improvements, such as more robust multi-modal generation techniques and enhanced texture generation models.