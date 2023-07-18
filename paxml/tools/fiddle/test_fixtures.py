# coding=utf-8
# Copyright 2022 The Pax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Various test fixtures."""

import dataclasses

import jax
from jax import numpy as jnp
from paxml import base_experiment
from paxml import base_task
from paxml import tasks_lib
from praxis import base_input
from praxis import base_model
from praxis import pax_fiddle


class SampleModel(base_model.BaseModel):
  my_setting: int = 1
  derived_setting: int = 2
  derived_list_setting: list[int] = dataclasses.field(
      default_factory=lambda: [3, 4]
  )


class SampleExperiment(base_experiment.BaseExperiment):
  """Fake experiment used for unit testing."""

  FOO_SETTING = 4123

  def datasets(self) -> list[pax_fiddle.Config[base_input.BaseInput]]:
    return []

  @property
  def derived_setting(self):
    return self.FOO_SETTING * 2

  @property
  def derived_list_setting(self):
    return [self.FOO_SETTING, self.derived_setting]

  def task(self) -> pax_fiddle.Config[base_task.BaseTask]:
    return pax_fiddle.Config(
        tasks_lib.SingleTask,
        model=pax_fiddle.Config(
            SampleModel,
            my_setting=self.FOO_SETTING,
            derived_setting=self.derived_setting,
            derived_list_setting=self.derived_list_setting,
        ),
    )


class SampleShardedExperiment(SampleExperiment):

  def task(self) -> pax_fiddle.Config[base_task.BaseTask]:
    task = super().task()
    task.model.activation_split_dims_mapping.out = ["foo_axis", "bar_axis"]
    return task


class SampleExperimentWithDatasets(SampleExperiment):

  def datasets(self) -> list[pax_fiddle.Config[base_input.BaseInput]]:
    return [
        pax_fiddle.Config(
            base_input.BaseInput,
            is_training=True,
            batch_size=1024,
        ),
        pax_fiddle.Config(
            base_input.BaseInput,
            is_training=False,
            batch_size=128,
        ),
    ]


class SampleExperimentWithDecoderDatasets(SampleExperiment):

  def decoder_datasets(self) -> list[pax_fiddle.Config[base_input.BaseInput]]:
    return [
        pax_fiddle.Config(
            base_input.BaseInput,
            is_training=False,
            batch_size=256,
        ),
    ]


class SampleInputSpecsProvider(base_input.BaseInputSpecsProvider):

  def get_input_specs(self) -> base_input.NestedShapeDtypeStruct:
    return {
        "inputs": jax.ShapeDtypeStruct([16, 32], jnp.int32),
    }


class SampleExperimentWithInputSpecsProvider(SampleExperiment):

  def get_input_specs_provider_params(
      self,
  ) -> pax_fiddle.Config[base_input.BaseInputSpecsProvider]:
    return pax_fiddle.Config(SampleInputSpecsProvider)


class SampleExperimentWithInitFromCheckpointRules(SampleExperiment):
  """Sample experiment with init_from_checkpoint_rules."""

  def task(self):
    task = super().task()
    ckpt_model = SampleExperimentWithInputSpecsProvider()
    task.train.init_from_checkpoint_rules = {
        "/path/to/my/checkpoint": pax_fiddle.Config(
            tasks_lib.CheckpointLoadingRules,
            task_p=ckpt_model.task(),
            load_rules=[(r"(.*)", "{}")],
            ignore_rules=[],
            load_opt_states=False,
            load_step=False,
            safe_load=True,
            step=532000,
            input_specs_provider_p=ckpt_model.get_input_specs_provider_params(),
        )
    }
    return task
