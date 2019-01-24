/**
 *  @file
 *  @copyright defined in eos/LICENSE.txt
 */
#pragma once

#include <eosiolib/asset.hpp>
#include <eosiolib/eosio.hpp>

#include <string>

namespace eosiosystem {
   class system_contract;
}

namespace eosio {

   using std::string;

   enum  class trade_type:int64_t {
      equal_ratio=1,
      trade_type_count
   };

   enum  class coin_type:int64_t {
      coin_base=1,
      coin_market,
      trade_type_count
   };

   class market_maker : public contract {
      public:
         market_maker( account_name self ):contract(self){}
         void addmarket(account_name market_maker,trade_type type,string coinbase_symbol,asset coinbase_amount,account_name coinbase_account,uint64_t base_weight,
               string coinmarket_symbol,asset coinmarket_amount,account_name coinmarket_account,uint64_t market_weight);//新增一个交易对    

         void addmortgage(int64_t trade_id,account_name market_maker,account_name recharge_account,asset recharge_amount,coin_type type);//增加抵押
         void claimmortgage(int64_t trade_id,account_name market_maker,asset claim_amount,coin_type type);//取出抵押     是否需要冻结一段时间有待考虑

         //需要有一个查询功能  根据做市商查询这个做市商所有的交易对
         //散户使用的功能就是做交易
         void exchange(int64_t trade_id,account_name market_maker,account_name account_base,account_name account_market,asset amount,coin_type type);
         //冻结交易对
         void frozenmarket(int64_t trade_id,account_name market_maker);
         //解冻交易对
         void trawmarket(int64_t trade_id,account_name market_maker);
      private:

         struct coin {
            string symbol;    //币种
            asset  amount;    //抵押数额
            account_name   coin_maker;//做市商账户
           
         };

         struct trade_pair {  //交易对
            uint64_t trade_id;        //交易对的唯一ID     这个会写入内存表里面
            trade_type type;        //交易类型 用于表明是等比例或者bancor或者其他交易类型  这个也用于计算公式的设置
            coin  coin_base;        //一般指共识程度较高的币种    做市上一般用这个币种来担保coin_market
            coin  coin_market;      //一般指做市上自己的币种   和coin_base属于相互担保的关系
            account_name   market_maker;// 做市商的账户     抵押中继链资源等都需要这个账户   暂时没有抵押资源这些操作
            uint64_t  base_weight;      //coin_base 比重
            uint64_t  market_weight;      //coin_base 比重
            bool  isactive =true;      //交易对状态，用于做市商紧急叫停交易对

            uint64_t primary_key()const { return trade_id; }
         };
         
         typedef eosio::multi_index<N(tradepairs), trade_pair> tradepairs;
   };

   EOSIO_ABI( market_maker, (addmarket)(addmortgage)(claimmortgage)(exchange)(frozenmarket)(trawmarket) )
} /// namespace eosio
