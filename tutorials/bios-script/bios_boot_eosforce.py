#!/usr/bin/env python

import argparse
import json
import os
import subprocess
import sys
import time
from forceio import *

def importKeys():
    keys = {}
    for a in datas.initAccountsKeys:
        key = a[1]
        if not key in keys:
            keys[key] = True
            cleos('wallet import --private-key ' + key)

def createNodeDir(nodeIndex, bpaccount, key):
    dir = datas.args.nodes_dir + ('%02d-' % nodeIndex) + bpaccount['name'] + '/'
    run('rm -rf ' + dir)
    run('mkdir -p ' + dir)

def createNodeDirs(inits, keys):
    for i in range(0, len(inits)):
        createNodeDir(i + 1, datas.initProducers[i], keys[i])

def startNode(nodeIndex, bpaccount, key):
    dir = datas.args.nodes_dir + ('%02d-' % nodeIndex) + bpaccount['name'] + '/'
    otherOpts = ''.join(list(map(lambda i: ('    --p2p-peer-address 127.0.0.1:%d1%02d' % (datas.args.use_port, i)), range(nodeIndex - 1))))
    if not nodeIndex: otherOpts += (
        '    --plugin eosio::history_plugin'
        '    --plugin eosio::history_api_plugin'
    )


    print('bpaccount ', bpaccount)
    print('key ', key, ' ', key[1])

    cmd = (
        datas.args.nodeos +
        '    --blocks-dir ' + os.path.abspath(dir) + '/blocks'
        '    --config-dir ' + os.path.abspath(dir) + '/../../config'
        '    --data-dir ' + os.path.abspath(dir) +
        ('    --http-server-address 0.0.0.0:%d0%02d' % (datas.args.use_port, nodeIndex)) +
        ('    --p2p-listen-endpoint 0.0.0.0:%d1%02d' % (datas.args.use_port, nodeIndex)) +
        '    --max-clients ' + str(datas.maxClients) +
        '    --p2p-max-nodes-per-host ' + str(datas.maxClients) +
        '    --enable-stale-production'
        '    --producer-name ' + bpaccount['name'] +
        '    --signature-provider=' + bpaccount['bpkey'] + '=KEY:' + key[1] +
        '    --contracts-console ' +
        '    --plugin eosio::http_plugin' +
        '    --plugin eosio::chain_api_plugin' +
        '    --plugin eosio::producer_plugin' +
        otherOpts)
    with open(dir + '../' + bpaccount['name'] + '.log', mode='w') as f:
        f.write(cmd + '\n\n')
    background(cmd + '    2>>' + dir + '../' + bpaccount['name'] + '.log')

def startProducers(inits, keys):
    for i in range(0, len(inits)):
        startNode(i + 1, datas.initProducers[i], keys[i])

def listProducers():
    cleos('get table eosio eosio bps')

def stepKillAll():
    run('killall keosd nodeos || true')
    sleep(.5)

def stepStartWallet():
    rm(datas.wallet_dir)
    run('mkdir -p ' + datas.wallet_dir)
    background(datas.args.keosd + 
        ( ' --unlock-timeout 999999999' +
          ' --http-server-address 0.0.0.0:%d666' +
          ' --wallet-dir %s' ) % (datas.args.use_port, datas.wallet_dir))
    sleep(.4)

def stepCreateWallet():
    run('mkdir -p ' + datas.wallet_dir)
    cleos('wallet create --file ./pw')

def stepStartProducers():
    startProducers(datas.initProducers, datas.initProducerSigKeys)
    sleep(7)
    stepSetFuncs()

def stepCreateNodeDirs():
    createNodeDirs(datas.initProducers, datas.initProducerSigKeys)
    sleep(0.5)

def stepLog():
    run('tail -n 1000 ' + datas.args.nodes_dir + 'biosbpa.log')
    cleos('get info')
    print('you can use \"alias cleost=\'%s\'\" to call cleos to testnet' % datas.args.cleos)

def stepMkConfig():
    global datas
    with open(datas.config_dir + '/genesis.json') as f:
        a = json.load(f)
        datas.initAccounts = a['initial_account_list']
        datas.initProducers = a['initial_producer_list']
    with open(datas.config_dir + '/keys/sigkey.json') as f:
        a = json.load(f)
        datas.initProducerSigKeys = a['keymap']
    with open(datas.config_dir + '/keys/key.json') as f:
        a = json.load(f)
        datas.initAccountsKeys = a['keymap']
    datas.maxClients = len(datas.initProducers) + 10

def cpContract(account):
    run('mkdir -p %s/%s/' % (datas.config_dir, account))
    run('cp ' + datas.contracts_dir + ('/%s/%s.abi ' % (account, account)) + datas.config_dir + "/" + account + "/")
    run('cp ' + datas.contracts_dir + ('/%s/%s.wasm ' % (account, account)) + datas.config_dir + "/" + account + "/")

def stepMakeGenesis():
    rm(datas.config_dir)
    run('mkdir -p ' + datas.config_dir)
    run('mkdir -p ' + datas.config_dir + '/keys/' )

    run('cp ' + datas.contracts_dir + '/force.token/force.token.abi ' + datas.config_dir)
    run('cp ' + datas.contracts_dir + '/force.token/force.token.wasm ' + datas.config_dir)
    run('cp ' + datas.contracts_dir + '/force.system/force.system.abi ' + datas.config_dir)
    run('cp ' + datas.contracts_dir + '/force.system/force.system.wasm ' + datas.config_dir)
    run('cp ' + datas.contracts_dir + '/force.msig/force.msig.abi ' + datas.config_dir)
    run('cp ' + datas.contracts_dir + '/force.msig/force.msig.wasm ' + datas.config_dir)
    run('cp ' + datas.contracts_dir + '/force.relay/force.relay.abi ' + datas.config_dir)
    run('cp ' + datas.contracts_dir + '/force.relay/force.relay.wasm ' + datas.config_dir)
    
    run('cp ./genesis-data/config.ini ' + datas.config_dir)

    cpContract('relay.token')
        
    run(datas.args.root + 'build/programs/genesis/genesis')
    run('mv ./genesis.json ' + datas.config_dir)
    run('mv ./activeacc.json ' + datas.config_dir)
    
    run('mv ./key.json ' + datas.config_dir + '/keys/')
    run('mv ./sigkey.json ' + datas.config_dir + '/keys/')

def createMap(chain, token_account):
    pushAction("force.relay", "newchannel", "eosforce", 
        '{"chain":"%s","checker":"biosbpa","id":"","mroot":""}' % (chain))
    pushAction("force.relay", "newmap", "eosforce", 
        '{"chain":"%s","type":"token","id":"","act_account":"%s","act_name":"transfer","account":"relay.token","data":""}' % (chain, token_account))

def createMapToken(chain, issuer, asset):
    pushAction('relay.token', 'create', issuer,
        '{"issuer":"%s","chain":"%s","maximum_supply":"%s"}' % (issuer,chain,asset))


def stepSetFuncs():
    # we need set some func start block num
    # setFee('eosio', 'setconfig', 100, 100000, 1000000, 1000)

    # some config to set
    print('stepSetFuncs')

    pubKeys = {}
    for a in datas.initAccounts:
        pubKeys[a['name']] = str(a['key'])
    print(pubKeys['eosforce'])

    cleos(('set account permission %s active ' + 
          '\'{"threshold": 1,"keys": [{"key": "%s","weight": 1}],"accounts": [{"permission":{"actor":"relay.token","permission":"force.code"},"weight":1}]}\'') % 
          ("eosforce", pubKeys['eosforce']))

    setContract('relay.token')
    setFee('relay.token', 'on',       15000, 0, 0, 0)
    setFee('relay.token', 'create',   15000, 0, 0, 0)
    setFee('relay.token', 'issue',    15000, 0, 0, 0)
    setFee('relay.token', 'transfer', 1000,  0, 0, 0)

    createMap("eosforce", "force.token")
    #createMap("side", "force.token")

    createMapToken('eosforce','eosforce', "10000000.0000 EOS")
    createMapToken('eosforce','eosforce', "10000000.0000 SYS")
    createMapToken('eosforce','eosforce', "10000000.0000 SSS")
    createMapToken('side','eosforce', "10000000.0000 EOS")
    createMapToken('side','eosforce', "10000000.0000 SYS")
    createMapToken('side','eosforce', "10000000.0000 SSS")

def clearData():
    stepKillAll()
    rm(datas.config_dir)
    rm(datas.nodes_dir)
    rm(datas.wallet_dir)
    rm(datas.log_path)
    rm(os.path.abspath('./pw'))
    rm(os.path.abspath('./config.ini'))

def restart():
    stepKillAll()
    stepMkConfig()
    stepStartWallet()
    stepCreateWallet()
    importKeys()
    stepStartProducers()
    stepLog()

# =======================================================================================================================
# Command Line Arguments  
commands = [
    ('k', 'kill',           stepKillAll,                False,   "Kill all nodeos and keosd processes"),
    ('c', 'clearData',      clearData,                  False,   "Clear all Data, del ./nodes and ./wallet"),
    ('r', 'restart',        restart,                    False,   "Restart all nodeos and keosd processes"),
    ('g', 'mkGenesis',      stepMakeGenesis,            True,    "Make Genesis"),
    ('m', 'mkConfig',       stepMkConfig,               True,    "Make Configs"),
    ('w', 'wallet',         stepStartWallet,            True,    "Start keosd, create wallet, fill with keys"),
    ('W', 'createWallet',   stepCreateWallet,           True,    "Create wallet"),
    ('i', 'importKeys',     importKeys,                 True,    "importKeys"),
    ('D', 'createDirs',     stepCreateNodeDirs,         True,    "create dirs for node and log"),
    ('P', 'start-prod',     stepStartProducers,         True,    "Start producers"),
    ('l', 'log',            stepLog,                    True,    "Show tail of node's log"),
]

parser = argparse.ArgumentParser()

parser.add_argument('--cleos', metavar='', help="Cleos command", default='build/programs/cleos/cleos')
parser.add_argument('--nodeos', metavar='', help="Path to nodeos binary", default='build/programs/nodeos/nodeos')
parser.add_argument('--keosd', metavar='', help="Path to keosd binary", default='build/programs/keosd/keosd')

parserArgsAndRun(parser, commands)
