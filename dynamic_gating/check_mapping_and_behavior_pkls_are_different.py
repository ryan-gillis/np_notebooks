import np_session
import np_tools 

# sessions = ('1226251663_636740_20221115', '1226528572_636740_20221116', '1226780656_636740_20221117', '1227622013_637483_20221121', '1227855488_637483_20221122', '1228018071_637483_20221123', '1229654875_638387_20221130', '1230962048_637488_20221206', '1231219674_637488_20221207', '1231476077_637488_20221208', '1232725697_640890_20221213', '1232954220_640890_20221214', '1233182785_640890_20221215')

# for s in sessions:
#     session = np_session.Session(s)

#     behavior_pickle_file = session.npexp_path / f'{session}.behavior.pkl'
#     mapping_pickle_file = session.npexp_path / f'{session}.mapping.pkl'
#     # print(behavior_pickle_file.stat().st_size, mapping_pickle_file.stat().st_size)
    
    
#     correct_mapping_pickle_on_rig = (
#         np_tools.get_files_created_between(session.rig.paths['Camstim'], '*mapping*pkl', session.start, session.end)[0]
#     )
   
#     np_tools.copy(correct_mapping_pickle_on_rig, mapping_pickle_file)
    
sessions = (1194643724, 1215407402, 1215593634, 1215803244, 1216100684, 1217019372)
for s in sessions:
    session = np_session.Session(s)
    sync_file = session.npexp_path / f'{session}.sync'
    sync_files_on_rig = (
        np_tools.get_files_created_between(session.rig.paths['Sync'], '*', session.start, session.end)
    )
    if not sync_files_on_rig:
        continue
    
    print(sync_file.stat().st_size, *(_.stat().st_size for _ in sync_files_on_rig))
    # print(sync_files_on_rig[0])
    