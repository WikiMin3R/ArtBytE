// Copyright (c) 2009-2012 The Bitcoin developers
// Distributed under the MIT/X11 software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#include <boost/assign/list_of.hpp> // for 'map_list_of()'
#include <boost/foreach.hpp>

#include "checkpoints.h"

#include "txdb.h"
#include "main.h"
#include "uint256.h"


static const int nCheckpointSpan = 500;

 namespace Checkpoints
 {
    typedef std::map<int, uint256> MapCheckpoints;

    //
    // What makes a good checkpoint block?
    // + Is surrounded by blocks with reasonable timestamps
    //   (no blocks before with a timestamp after, none after with
    //    timestamp before)
    // + Contains no strange transactions
    //
    static MapCheckpoints mapCheckpoints =
        boost::assign::map_list_of
        ( 0000,   uint256("0x000002800739840e434b5d61dc3ba4c5f5d9525d7799ce92b63e16a04967aed3") ) // genesis
        ( 1001,   uint256("0xedc30dfebc2d6f242722ef3dc0fc7a674fa86eacc0c8afd491ad8c22efce09cb") ) // 25% PoS sufficiency
        ( 5005,   uint256("0xe4dd9a3b8d14b5465dc04af5a5f10fafc34aa524119fd0e01a087a66e08a8e76") ) // 50% PoS sufficiency
        ( 10001,  uint256("0x302c768ae44740e58e67dfe02c1f9e46daaf3a09aefe2fa5eb16b60ba44153a4") ) // 75% PoS sufficiency
        ( 14001,  uint256("0x703e4b61a1218d4270ad454db07e1f89c731688c505ba3d412279a5ca6952cdf") ) // 99% PoS Sufficiency
//      ( 872456, uint256("0xe4fd321ced1de06213d2e246b150b4bfd8c4aa0989965dce88f2a58668c64860") ) //
    ;

    // TestNet has no checkpoints
    static MapCheckpoints mapCheckpointsTestnet;

    bool CheckHardened(int nHeight, const uint256& hash)
    {
        MapCheckpoints& checkpoints = (TestNet() ? mapCheckpointsTestnet : mapCheckpoints);

        MapCheckpoints::const_iterator i = checkpoints.find(nHeight);
        if (i == checkpoints.end()) return true;
        return hash == i->second;
    }

    int GetTotalBlocksEstimate()
    {
        MapCheckpoints& checkpoints = (TestNet() ? mapCheckpointsTestnet : mapCheckpoints);

        if (checkpoints.empty())
            return 0;
        return checkpoints.rbegin()->first;
    }

    CBlockIndex* GetLastCheckpoint(const std::map<uint256, CBlockIndex*>& mapBlockIndex)
    {
        MapCheckpoints& checkpoints = (TestNet() ? mapCheckpointsTestnet : mapCheckpoints);

        BOOST_REVERSE_FOREACH(const MapCheckpoints::value_type& i, checkpoints)
        {
            const uint256& hash = i.second;
            std::map<uint256, CBlockIndex*>::const_iterator t = mapBlockIndex.find(hash);
            if (t != mapBlockIndex.end())
                return t->second;
        }
        return NULL;
    }

    // Automatically select a suitable sync-checkpoint 
    const CBlockIndex* AutoSelectSyncCheckpoint()
    {
        const CBlockIndex *pindex = pindexBest;
        // Search backward for a block within max span and maturity window
        while (pindex->pprev && pindex->nHeight + nCheckpointSpan > pindexBest->nHeight)
            pindex = pindex->pprev;
        return pindex;
    }

    // Check against synchronized checkpoint
    bool CheckSync(int nHeight)
    {
        const CBlockIndex* pindexSync = AutoSelectSyncCheckpoint();

        if (nHeight <= pindexSync->nHeight)
            return false;
        return true;
    }
}
