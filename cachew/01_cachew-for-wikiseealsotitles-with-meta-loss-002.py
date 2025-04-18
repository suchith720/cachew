# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_cachew-for-wikiseealsotitles-with-meta-loss.ipynb.

# %% auto 0
__all__ = []

# %% ../nbs/01_cachew-for-wikiseealsotitles-with-meta-loss.ipynb 3
import os,torch,json, torch.multiprocessing as mp, joblib, numpy as np, scipy.sparse as sp

from xcai.main import *
from xcai.basics import *

from xcai.models.cachew import CAW002, CachewConfig

# %% ../nbs/01_cachew-for-wikiseealsotitles-with-meta-loss.ipynb 5
os.environ['CUDA_VISIBLE_DEVICES'] = '2,3'
os.environ['WANDB_PROJECT'] = 'cachew_00-wikiseealsotitles'

# %% ../nbs/01_cachew-for-wikiseealsotitles-with-meta-loss.ipynb 7
if __name__ == '__main__':
    output_dir = '/home/aiscuser/scratch1/outputs/cachew/01_cachew-for-wikiseealsotitles-with-meta-loss-002'

    data_dir = '/data/datasets/benchmarks/'
    config_file = 'wikiseealsotitles'
    config_key = 'data_meta'
    
    meta_embed_init_file = '/data/datasets/ogb_weights/LF-WikiSeeAlsoTitles-320K/emb_weights.npy'
    
    meta_name = 'cat'

    input_args = parse_args()

    pkl_file = f'{input_args.pickle_dir}/cachew/wikiseealsotitles_data-meta_distilbert-base-uncased'
    pkl_file = f'{pkl_file}_sxc' if input_args.use_sxc_sampler else f'{pkl_file}_xcs'
    if input_args.only_test: pkl_file = f'{pkl_file}_only-test'
    pkl_file = f'{pkl_file}.joblib'

    do_inference = input_args.do_train_inference or input_args.do_test_inference or input_args.save_train_prediction or input_args.save_test_prediction or input_args.save_representation

    os.makedirs(os.path.dirname(pkl_file), exist_ok=True)
    block = build_block(pkl_file, config_file, input_args.use_sxc_sampler, config_key, do_build=input_args.build_block, only_test=input_args.only_test, 
                        n_slbl_samples=4, main_oversample=False, n_sdata_meta_samples=5, meta_oversample=False, train_meta_topk=5, test_meta_topk=3, 
                        data_dir=data_dir)
    block.test.dset.meta = {}

    args = XCLearningArguments(
        output_dir=output_dir,
        logging_first_step=True,
        per_device_train_batch_size=512,
        per_device_eval_batch_size=512,
        representation_num_beams=200,
        representation_accumulation_steps=10,
        save_strategy="steps",
        eval_strategy="steps",
        eval_steps=5000,
        save_steps=5000,
        save_total_limit=5,
        num_train_epochs=300,
        predict_with_representation=True,
        adam_epsilon=1e-6,
        warmup_steps=100,
        weight_decay=0.01,
        learning_rate=2e-4,
        representation_search_type='BRUTEFORCE',
    
        output_representation_attribute='data_enriched_repr',
        label_representation_attribute='data_repr',
        metadata_representation_attribute='data_repr',
        data_augmentation_attribute='data_repr',
        representation_attribute='data_enriched_repr',
        clustering_representation_attribute='data_enriched_repr',
    
        group_by_cluster=True,
        num_clustering_warmup_epochs=10,
        num_cluster_update_epochs=5,
        num_cluster_size_update_epochs=25,
        use_data_metadata_for_clustering=True,
        clustering_type='EXPO',
        minimum_cluster_size=2,
        maximum_cluster_size=1600,

        metric_for_best_model='P@1',
        load_best_model_at_end=True,
        target_indices_key='plbl2data_idx',
        target_pointer_key='plbl2data_data2ptr',
    
        use_distributional_representation=False,
        use_encoder_parallel=True,
        max_grad_norm=None,
        fp16=True,
    
        label_names=[f'{meta_name}2data_idx', f'{meta_name}2data_data2ptr', f'p{meta_name}2data_idx', f'p{meta_name}2data_data2ptr'],
                     
        prune_metadata=False,
        num_metadata_prune_warmup_epochs=10,
        num_metadata_prune_epochs=5,
        metadata_prune_batch_size=2048,
        prune_metadata_names=[f'{meta_name}_meta'],
        use_data_metadata_for_pruning=True,
    
        predict_with_augmentation=False,
        use_augmentation_index_representation=True,
    
        data_aug_meta_name=meta_name,
        augmentation_num_beams=None,
        data_aug_prefix=meta_name,
        use_label_metadata=False,
    
        data_meta_batch_size=2048,
        augment_metadata=False,
        num_metadata_augment_warmup_epochs=10,
        num_metadata_augment_epochs=5,
    
        use_cpu_for_searching=True,
        use_cpu_for_clustering=True,
    )

    config = CachewConfig(
        top_k_metadata = 5,
        num_metadata=block.train.dset.meta['cat_meta'].n_meta,
    
        data_aug_meta_prefix='cat2data', 
        lbl2data_aug_meta_prefix=None,

        data_enrich=True,
        lbl2data_enrich=False,
    
        margin=0.3,
        num_negatives=10,
        tau=0.1,
        apply_softmax=True,
    
        calib_margin=0.3,
        calib_num_negatives=10,
        calib_tau=0.1,
        calib_apply_softmax=False,
        calib_loss_weight=0.1,
        use_calib_loss=True,

        meta_loss_weight=0.5,
        use_meta_loss=True,
    
        use_query_loss=True, 
        use_encoder_parallel=True
    )
    
    model = CAW002.from_pretrained('sentence-transformers/msmarco-distilbert-base-v4', config=config)
    model.init_combiner_to_last_layer()
    
    meta_embeddings = torch.tensor(np.load(meta_embed_init_file), dtype=torch.float32)
    model.set_memory_embeddings(meta_embeddings)

    metric = PrecReclMrr(block.n_lbl, block.test.data_lbl_filterer, prop=block.train.dset.data.data_lbl,
                         pk=10, rk=200, rep_pk=[1, 3, 5, 10], rep_rk=[10, 100, 200], mk=[5, 10, 20])

    learn = XCLearner(
        model=model,
        args=args,
        train_dataset=block.train.dset,
        eval_dataset=block.test.dset,
        data_collator=block.collator,
        compute_metrics=metric,
    )

    if do_inference: os.environ['WANDB_MODE'] = 'disabled'
    
    main(learn, input_args, n_lbl=block.n_lbl)
    
