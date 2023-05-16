import tensorflow as tf
from tensorflow import keras
from keras import layers
from prediction_model.model_constants import *
import numpy as np


# def get_quantizable_model(vocab_size, embedding_dim, rnn_units):
#     input = keras.Input(shape=(1, vocab_size,), name="input")
#     embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim)
#     embedded_input = embedding(input)[0, :, :, :]
#     hidden_state = keras.Input(shape=(rnn_units,), name="lstm_hidden_state")
#     cell_state = keras.Input(shape=(rnn_units,), name="lstm_cell_state")
#     lstm = layers.LSTM(units=rnn_units, return_sequences=True,
#                                                            return_state=True,
#                                                            name="lstm",
#                        stateful=True)
#     lstm_output, new_hidden_state, new_cell_state = lstm(embedded_input)#), initial_state=[hidden_state, cell_state])
#     dense = tf.keras.layers.Dense(vocab_size)
#     output = dense(lstm_output)
#     model = keras.Model([input],#, hidden_state, cell_state],
#                         [output, new_hidden_state, new_cell_state])
#     model.compile()
#     return model

rng = np.random.default_rng()


def get_quantizable_model(model):
    input = keras.Input(shape=(1,), name="input")
    hidden_state = keras.Input(shape=(rnn_units), name="lstm_hidden_state")
    cell_state = keras.Input(shape=(rnn_units), name="lstm_cell_state")
    output, (new_hidden_state, new_cell_state) = model(
        input, states=[hidden_state, cell_state], return_state=True)
    model = keras.Model([input, hidden_state, cell_state],
                        [output, new_hidden_state, new_cell_state])
    return model


def representative_dataset():
    yield [rng.random((1, vocab_size), dtype=np.float32),
           rng.random((1, rnn_units), dtype=np.float32),
           rng.random((1, rnn_units), dtype=np.float32)]



def convert_to_tflite(model):
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.experimental_new_converter = True
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS,
                                           tf.lite.OpsSet.SELECT_TF_OPS]
    tflite_model = converter.convert()
    return tflite_model




class QuantOneStep:
    def __init__(self, interpreter, vocab):
        self.interpreter = interpreter
        self.vocab = vocab
        self.ids_from_chars = tf.keras.layers.StringLookup(
            vocabulary=list(vocab), mask_token=None)
        self.chars_from_ids = tf.keras.layers.StringLookup(
            vocabulary=self.ids_from_chars.get_vocabulary(), invert=True, mask_token=None)

    # @tf.function
    def get_probabilty_weights(self, inputs, states):
        # Convert strings to token IDs.
        input_chars = tf.strings.unicode_split(inputs, 'UTF-8')
        input_ids = np.float32(self.ids_from_chars([input_chars]))
        input_vectors = tf.one_hot(input_ids, vocab_size)
        self.interpreter.allocate_tensors()
        input_details = self.interpreter.get_input_details()
        output_details = self.interpreter.get_output_details()
        self.interpreter.set_tensor(input_details[2]["index"], input_ids)

        self.interpreter.set_tensor(input_details[0]["index"], states[0])
        self.interpreter.set_tensor(input_details[1]["index"], states[1])
        self.interpreter.invoke()
        result = self.interpreter.get_tensor(output_details[0]["index"])
        result = result[0, -1, :]
        states = self.interpreter.get_tensor(output_details[2]["index"])
        carry = self.interpreter.get_tensor(output_details[1]["index"])

        return result, (states, carry)