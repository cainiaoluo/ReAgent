#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates. All rights reserved.
import copy
import logging

import numpy as np
import torch
from reagent import types as rlt
from reagent.training.reward_network_trainer import RewardNetTrainer
from reagent.types import PreprocessedTrainingBatch


logger = logging.getLogger(__name__)


class RewardNetEvaluator:
    """ Evaluate reward networks """

    def __init__(self, trainer: RewardNetTrainer) -> None:
        self.trainer = trainer
        self.loss = []
        self.rewards = []
        self.best_model = None
        self.best_model_loss = 1e9

    # pyre-fixme[56]: Decorator `torch.no_grad(...)` could not be called, because
    #  its type `no_grad` is not callable.
    @torch.no_grad()
    def evaluate(self, eval_tdp: PreprocessedTrainingBatch):
        reward_net = self.trainer.reward_net
        reward_net_prev_mode = reward_net.training
        reward_net.eval()

        if isinstance(eval_tdp.training_input, rlt.PreprocessedRankingInput):
            reward = eval_tdp.training_input.slate_reward
        else:
            reward = eval_tdp.training_input.reward
        assert reward is not None

        loss = self.trainer.loss_fn(
            reward_net(eval_tdp.training_input).predicted_reward, reward
        )
        self.loss.append(loss.flatten().detach().cpu())
        self.rewards.append(reward.flatten().detach().cpu())

        reward_net.train(reward_net_prev_mode)

    @torch.no_grad()
    def evaluate_post_training(self):
        mean_loss = np.mean(self.loss)
        logger.info(f"Evaluation {self.trainer.loss_type}={mean_loss}")
        eval_res = {"loss": mean_loss, "rewards": torch.cat(self.rewards)}
        self.loss = []
        self.rewards = []

        if mean_loss < self.best_model_loss:
            self.best_model_loss = mean_loss
            self.best_model = copy.deepcopy(self.trainer.reward_net)

        return eval_res
