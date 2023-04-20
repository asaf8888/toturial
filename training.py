import tensorflow as tf
import keras
import re
import numpy
import os
from model import MyModel
from constants import *


the_bible_raw = open('bible.txt', 'r')
the_bible = the_bible_raw.readlines()
the_bible_raw.close()

the_bible = [x[re.search("\d+:\d+ *.", x).end(): ] for x in the_bible]
the_bible = [list(x) for x in the_bible]
the_bible = list(numpy.concatenate(the_bible).flat)
the_bible = list(map(lambda x: x.replace('\n', ' '), the_bible))
vocab = sorted(set(the_bible))
print(vocab)


ids_from_chars = tf.keras.layers.StringLookup(
    vocabulary=list(vocab), mask_token=None)

chars_from_ids = tf.keras.layers.StringLookup(
    vocabulary=ids_from_chars.get_vocabulary(), invert=True, mask_token=None)


def text_from_ids(ids):
    return tf.strings.reduce_join(chars_from_ids(ids), axis=-1)


ids_dataset = tf.data.Dataset.from_tensor_slices(ids_from_chars(the_bible))
sequences = ids_dataset.batch(SEQ_LENGTH + 1, drop_remainder=True)
dataset = sequences.map(lambda x: (x[:-1], x[1:]))

dataset = (
    dataset
    .shuffle(BUFFER_SIZE)
    .batch(BATCH_SIZE, drop_remainder=True)
    .prefetch(tf.data.experimental.AUTOTUNE))

# Length of the vocabulary in StringLookup Layer
vocab_size = len(ids_from_chars.get_vocabulary())
print(f"vocab size: {vocab_size}")

checkpoint_dir = './training_checkpoints'
# Name of the checkpoint files

checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt_{epoch}")

checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
    filepath=checkpoint_prefix,
    save_weights_only=True)

model = MyModel(vocab_size=vocab_size, embedding_dim=embedding_dim, rnn_units=rnn_units)
loss = tf.losses.SparseCategoricalCrossentropy(from_logits=True)
model.compile(optimizer='adam', loss=loss, metrics='accuracy')
history = model.fit(dataset, epochs=EPOCHS, callbacks=[checkpoint_callback])
