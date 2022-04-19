import logging

import numpy as np

from activation import sigmoid
from loss import mean_squared_error
from optimize import Optimizer

# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


class FullyConnectedNeuralNetwork:
    def __init__(
        self,
        in_dim_n: int,
        out_dim_n: int,
        learning_rate: float,
        batch_size: int,
        layer_type: str,
        optim_fn: str = "sgd",
        clip_grad_l2: float = None,
    ):
        self.in_dim_n = in_dim_n
        self.out_dim_n = out_dim_n
        self.weight = np.random.rand(in_dim_n, out_dim_n)
        self.x_in = None
        self.layer_type = layer_type or None
        self.EI = np.zeros((batch_size, out_dim_n))
        self.optim = Optimizer(optim_fn, learning_rate, clip_grad_l2)

    def forward(self, x: np.array, val_mode: bool = False):
        if not val_mode:
            self.x_in = np.copy(x)
        logger.debug(f"{x.shape = } {self.weight.shape = }")
        x_out = x @ self.weight
        logger.debug(f"{x_out.shape = }")
        logger.debug(f"{self.weight = }")

        return x_out

    def backward(
        self, y_out: np.array, y_true: np.array = None, agg_EI: np.array = None
    ):
        if self.layer_type == "out":
            logger.debug(f"{y_out.shape =}, {y_true.shape = }")
            EI = (y_out - y_true) @ y_out.T @ (1.0 - y_out)
            grad = self.x_in.T @ EI
            self.weight -= self.optim.optimize(grad)
            logger.debug(f"{EI.shape =}, {self.weight.shape = }")

            return np.einsum("ik,kj->ij", EI, self.weight.T)

        elif not self.layer_type == "hidden":
            logger.debug(f"{self.EI.shape =} {y_out.shape =}")
            self.EI += agg_EI @ (y_out.T @ (1.0 - y_out))
            logger.debug(f"{self.EI.shape =} {self.x_in.shape =}")
            grad = self.x_in.T @ self.EI
            self.weight -= self.optim.optimize(grad)


class BasicNeuralNetwork:
    def __init__(
        self,
        in_dim_n: int,
        hidden_dim_n: int,
        out_dim_n: int,
        epoch: int,
        learning_rate: float,
        batch_size: int,
        optimize_fn: str = "sgd",
        clip_grad_l2: float = None,
    ):
        self.hidden_layer = FullyConnectedNeuralNetwork(
            in_dim_n,
            hidden_dim_n,
            learning_rate,
            batch_size,
            "hidden",
            optimize_fn,
            clip_grad_l2,
        )
        self.out_layer = FullyConnectedNeuralNetwork(
            hidden_dim_n,
            out_dim_n,
            learning_rate,
            batch_size,
            "out",
            optimize_fn,
            clip_grad_l2,
        )
        self.epoch = epoch
        self.batch_size = batch_size
        self.hidden_mat = None
        self.out_mat = None
        self.norm = None
        self.val_mode = False

    def train(self, x_in: np.array, y: np.array, x_valid: np.array = np.nan, y_valid: np.array = np.nan):
        result = []
        max_epoch = self.epoch

        x_batch = self._batch(x_in) #, normalize=True)
        y_batch = self._batch(y)

        self.val_mode = not (np.isnan(x_valid.all()) or np.isnan(y_valid.all()))
        if self.val_mode:
            x_val_batch = self._batch(x_valid) #, normalize=True)
            y_val_batch = self._batch(y_valid)
            val_result = []
        #     zipped_data = zip((x_iter, y_iter), (x_val_iter, y_val_iter))
        # else:
        #     zipped_data =

        while self.epoch > 0:
            x_iter, y_iter = np.copy(x_batch), np.copy(y_batch)
            if self.val_mode:
                x_val_iter, y_val_iter = np.copy(x_val_batch), np.copy(y_val_batch)
                for n_iter, (x, y_true, x_val, y_val) in enumerate(zip(x_iter, y_iter, x_val_iter, y_val_iter)):
                    self.fit(x)
                    loss = mean_squared_error(self.out_mat, y_val)

                    agg_EI = self.out_layer.backward(self.out_mat, y_true=y_true)
                    self.hidden_layer.backward(self.hidden_mat, y_true=y_true, agg_EI=agg_EI)

                    self.fit(x_val, val_mode=True)
                    val_loss = mean_squared_error(self.out_mat, y_val)

                    print(
                        f"Epoch: {max_epoch - self.epoch}, Training Iteration: {n_iter}, Loss: {loss} ... Validating Iteration: {n_iter}, Loss: {val_loss}"
                    )
                result.append(loss)
                val_result.append(val_loss)

            else:
                for n_iter, (x, y_true) in enumerate(zip(x_iter, y_iter)):
                    self.fit(x)

                    loss = mean_squared_error(self.out_mat, y_true)
                    print(
                        f"Epoch: {max_epoch - self.epoch}, Training Iteration: {n_iter}, Loss: {loss}"
                    )
                    result.append(loss)

                    agg_EI = self.out_layer.backward(self.out_mat, y_true=y_true)
                    self.hidden_layer.backward(self.hidden_mat, y_true=y_true, agg_EI=agg_EI)

            self.epoch += -1

        if self.val_mode:
            return result, val_result

        return result

    def _batch(self, x_in: np.array, normalize: bool = False):
        x = np.copy(x_in)
        if normalize:
            x = self._normalize(x)
        end = len(x)
        return np.array([x[idx: min(idx + self.batch_size, end)] for idx in range(0, end, self.batch_size)])

    def fit(self, x: np.array, val_mode: bool = False):
        x = self.hidden_layer.forward(x, val_mode=val_mode)
        self.hidden_mat = sigmoid(x)
        x = self.out_layer.forward(self.hidden_mat, val_mode=val_mode)
        self.out_mat = sigmoid(x)

    def _normalize(self, x):
        if not self.val_mode:
            self.norm = np.linalg.norm(x)
        return x / self.norm

    def drop_out(self, x):
        pass
