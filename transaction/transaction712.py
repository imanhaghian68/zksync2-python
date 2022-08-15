from dataclasses import dataclass
from typing import Union
import sys
import rlp
from eth_typing import Address, ChecksumAddress, HexStr
from rlp.sedes import big_endian_int, binary
from rlp.sedes import List as rlpList

from web3.types import Wei, Nonce
from protocol.request.request_types import Eip712Meta


@dataclass
class Transaction712:
    nonce: Nonce
    gas_price: int
    gas_limit: int
    to: Union[Address, ChecksumAddress, str]
    value: int
    data: Union[bytes, HexStr]
    chain_id: int
    meta: Eip712Meta


def int_to_bytes(x: int) -> bytes:
    return x.to_bytes((x.bit_length() + 7) // 8, byteorder=sys.byteorder)


def get_data(data: Union[bytes, HexStr]) -> bytes:
    if isinstance(data, bytes):
        return data
    if data.startswith("0x"):
        data = data[2:]
    return bytes.fromhex(data)


def _get_v(signature) -> bytes:
    v_bytes = bytes()
    # TODO: getV[0] is big endian or little , and what is the bytes amount??
    if signature.v != 0:
        v_bytes = signature.v
    return v_bytes


def _encode_address(addr: Union[Address, ChecksumAddress, str]) -> bytes:
    if len(addr) == 0:
        return bytes()
    if isinstance(addr, bytes):
        return addr
    if addr.startswith("0x"):
        addr = addr[2:]
    return bytes.fromhex(addr)


def _encode_with_signature(tx712: Transaction712, signature):
    meta = tx712.meta

    factory_deps_data = []
    factory_deps_elements = None
    factory_deps = meta["factoryDeps"]
    if factory_deps is not None and len(factory_deps) > 0:
        factory_deps_data = factory_deps
        factory_deps_elements = [binary for _ in range(len(factory_deps_data))]

    aa_data = []
    aa_data_elements = None
    aa = meta["aaParams"]
    if aa is not None:
        aa_data = [
            bytes.fromhex(aa["from"]),
            aa["signature"]
        ]
        aa_data_elements = [binary, binary]

    class InternalRepresentation(rlp.Serializable):
        fields = [
            ('nonce', big_endian_int),
            ('gasPrice', big_endian_int),
            ('gasLimit', big_endian_int),
            ('to', binary),  # addresses that start with zeros should be encoded with the zeros included,
            # not as numeric values, TODO: for null values needs to be text ???
            ('value', big_endian_int),
            ('data', binary),
            ('v', binary),
            ('r', binary),
            ('s', binary),
            ('chain_id', big_endian_int),
            ('feeToken', binary),
            ('ergsPerPubdata', big_endian_int),
            ('factoryDeps', rlpList(elements=factory_deps_elements, strict=False)),
            ('aaParams', rlpList(elements=aa_data_elements, strict=False))
        ]

    value = InternalRepresentation(
        nonce=tx712.nonce,
        gasPrice=tx712.gas_price,
        gasLimit=tx712.gas_limit,
        to=_encode_address(tx712.to),
        value=tx712.value,
        data=get_data(tx712.data),
        v=_get_v(signature),
        r=int_to_bytes(signature.r),  # TODO: must be lstrip(trim leading by default), need check int or bytearray
        s=int_to_bytes(signature.r),  # TODO: must be lstrip(trim leading by default), need check int or bytearray
        chain_id=tx712.chain_id,
        feeToken=_encode_address((meta["feeToken"])),
        ergsPerPubdata=meta["ergsPerPubdata"],
        factoryDeps=factory_deps_data,
        aaParams=aa_data
    )
    return rlp.encode(value, infer_serializer=True, cache=False)


def _encode(tx712: Transaction712):
    meta = tx712.meta

    factory_deps_data = []
    factory_deps_elements = None
    factory_deps = meta["factoryDeps"]
    if factory_deps is not None and len(factory_deps) > 0:
        factory_deps_data = factory_deps
        factory_deps_elements = [binary for _ in range(len(factory_deps_data))]

    aa_data = []
    aa_data_elements = None
    aa = meta["aaParams"]
    if aa is not None:
        aa_data = [
            bytes.fromhex(aa["from"]),
            aa["signature"]
        ]
        aa_data_elements = [binary, binary]

    class InternalRepresentation(rlp.Serializable):
        fields = [
            ('nonce', big_endian_int),
            ('gasPrice', big_endian_int),
            ('gasLimit', big_endian_int),
            ('to', binary),
            ('value', big_endian_int),
            ('data', binary),
            ('chain_id', big_endian_int),
            ('feeToken', binary),
            ('ergsPerPubdata', big_endian_int),
            ('factoryDeps', rlpList(elements=factory_deps_elements, strict=False)),
            ('aaParams', rlpList(elements=aa_data_elements, strict=False))
        ]

    value = InternalRepresentation(
        nonce=tx712.nonce,
        gasPrice=tx712.gas_price,
        gasLimit=tx712.gas_limit,
        to=_encode_address(tx712.to),
        value=tx712.value,
        data=get_data(tx712.data),
        chain_id=tx712.chain_id,
        feeToken=_encode_address(meta["feeToken"]),
        ergsPerPubdata=meta["ergsPerPubdata"],
        factoryDeps=factory_deps_data,
        aaParams=aa_data
    )
    return rlp.encode(value, infer_serializer=True, cache=False)


class Transaction712Encoder:

    EIP_712_TX_TYPE = b'\x71'

    @classmethod
    def encode(cls, tx712: Transaction712, signature=None) -> bytes:
        if signature is not None:
            ret = _encode_with_signature(tx712, signature)
            return cls.EIP_712_TX_TYPE + ret
        return cls.EIP_712_TX_TYPE + _encode(tx712)

# import rlp
# from rlp.sedes import big_endian_int, binary
# from rlp.sedes import List as rlpList
# from transaction.transaction import TransactionBase, TransactionType
#
#
# class Transaction712:
#     # EIP_712_TX_TYPE = b'\x70'
#
#     def __init__(self, transaction: TransactionBase, chain_id):
#         self.transaction = transaction
#         self.chain_id = chain_id
#
#     def _get_withdraw_token(self, value: str) -> bytes:
#         if self.transaction.get_type() == TransactionType.WITHDRAW:
#             return bytes.fromhex(value)
#         else:
#             # INFO: must be empty byte array
#             return bytes()
#
#     def as_rlp_values(self, signature=None):
#         transaction_request = self.transaction.transaction_request()
#         maybe_empty_lst = []
#         elements_to_process = None
#         if self.transaction.get_type() == TransactionType.DEPLOY:
#             maybe_empty_lst = self.transaction.factory_deps
#             elements_to_process = [binary for _ in range(len(maybe_empty_lst))]
#
#         vals = transaction_request.values
#
#         for entry in ['to', 'feeToken', 'withdrawToken']:
#             address_like = vals[entry]
#             if address_like.startswith("0x"):
#                 vals[entry] = address_like[2:]
#
#         withdraw_token = self._get_withdraw_token(vals['withdrawToken'])
#
#         if signature is not None:
#             class InternalRepresentation(rlp.Serializable):
#                 fields = [
#                     ('nonce', big_endian_int),
#                     ('gasPrice', big_endian_int),
#                     ('gasLimit', big_endian_int),
#                     ('to', binary),  # addresses that start with zeros should be encoded with the zeros included,
#                     # not as numeric values, TODO: for null values needs to be text ???
#                     ('value', big_endian_int),
#                     ('data', binary),
#                     ('v', binary),
#                     ('r', binary),
#                     ('s', binary),
#                     ('chain_id', big_endian_int),
#                     ('feeToken', binary),
#                     ('withdrawToken', binary),
#                     ('ergsPerStorage', big_endian_int),
#                     ('ergsPerPubdata', big_endian_int),
#                     ('factoryDeps', rlpList(elements=elements_to_process, strict=False))
#                 ]
#
#             v_bytes = bytes()
#             # TODO: getV[0] is big endian or little , and what is the bytes amount??
#             if signature.v == 0:
#                 v_bytes = bytes(signature.v)
#
#             value = InternalRepresentation(
#                 nonce=vals['nonce'],
#                 gasPrice=vals['gasPrice'],
#                 gasLimit=vals['gasLimit'],
#                 to=bytes.fromhex(vals['to']),
#                 value=vals['value'],
#                 data=vals['data'],
#                 v=v_bytes,
#                 r=bytes(signature.r),  # TODO: must be lstrip(trim leading by default)
#                 s=bytes(signature.s),  # TODO: must be lstrip(trim leading by default)
#                 chain_id=self.chain_id,
#                 feeToken=bytes.fromhex(vals['feeToken']),
#                 withdrawToken=withdraw_token,
#                 ergsPerStorage=vals['ergsPerStorage'],
#                 ergsPerPubdata=vals['ergsPerPubdata'],
#                 factoryDeps=[maybe_empty_lst])
#             result = rlp.encode(value, infer_serializer=False, cache=False)
#         else:
#             class InternalRepresentation(rlp.Serializable):
#                 fields = [
#                     ('nonce', big_endian_int),
#                     ('gasPrice', big_endian_int),
#                     ('gasLimit', big_endian_int),
#                     ('to', binary),  # addresses that start with zeros should be encoded with the zeros included,
#                     # not as numeric values, TODO: for null values needs to be text ???
#                     ('value', big_endian_int),
#                     ('data', binary),
#                     ('chain_id', big_endian_int),
#                     ('feeToken', binary),
#                     ('withdrawToken', binary),
#                     ('ergsPerStorage', big_endian_int),
#                     ('ergsPerPubdata', big_endian_int),
#                     ('factoryDeps', rlpList(elements=elements_to_process, strict=False))
#                 ]
#
#             value = InternalRepresentation(
#                 nonce=vals['nonce'],
#                 gasPrice=vals['gasPrice'],
#                 gasLimit=vals['gasLimit'],
#                 to=bytes.fromhex(vals['to']),
#                 value=vals['value'],
#                 data=vals['data'],
#                 chain_id=self.chain_id,
#                 feeToken=bytes.fromhex(vals['feeToken']),
#                 withdrawToken=withdraw_token,
#                 ergsPerStorage=vals['ergsPerStorage'],
#                 ergsPerPubdata=vals['ergsPerPubdata'],
#                 # TODO: CHECK TYPE MUST BE List of Bytes
#                 factoryDeps=maybe_empty_lst
#             )
#             result = rlp.encode(value, infer_serializer=True, cache=False)
#         return result