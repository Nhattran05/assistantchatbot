from nemo.core.classes import ModelPT

asr_model = ModelPT.from_pretrained(model_name="nvidia/parakeet-ctc-0.6b-vi")
asr_model.save_to("parakeet-ctc-0.6b-vi.nemo")

diar_model = ModelPT.from_pretrained(model_name="nvidia/diar_streaming_sortformer_4spk-v2")
diar_model.save_to("diar_streaming_sortformer_4spk-v2.nemo")